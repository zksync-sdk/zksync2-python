from typing import Union, Type

from eth_account.signers.base import BaseAccount
from eth_typing import HexStr, Address
from eth_utils import event_signature_to_log_topic, add_0x_prefix
from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware
from web3.types import TxReceipt

from zksync2.account.utils import (
    deposit_to_request_execute,
    prepare_transaction_options,
)
from zksync2.core.types import (
    BridgeAddresses,
    ZksMessageProof,
    EthBlockParams,
    DepositTransaction,
    ADDRESS_DEFAULT,
    L1ToL2Log,
    RequestExecuteCallMsg,
    FullDepositFee,
    L1BridgeContracts,
    TransactionOptions,
)
from zksync2.core.utils import (
    RecommendedGasLimit,
    to_bytes,
    is_eth,
    apply_l1_to_l2_alias,
    get_custom_bridge_data,
    BOOTLOADER_FORMAL_ADDRESS,
    undo_l1_to_l2_alias,
    DEPOSIT_GAS_PER_PUBDATA_LIMIT,
)
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.utils import (
    zksync_abi_default,
    l1_bridge_abi_default,
    get_erc20_abi,
    l2_bridge_abi_default,
)
from zksync2.module.request_types import EIP712Meta
from zksync2.transaction.transaction_builders import TxFunctionCall


def check_base_cost(base_cost: int, value: int):
    if base_cost > value:
        raise RuntimeError(
            f"The base cost of performing the priority operation is higher than"
            f" the provided value parameter"
            f" for the transaction: base_cost: ${base_cost},"
            f" provided value: ${value}`"
        )


class WalletL1:
    DEPOSIT_GAS_PER_PUBDATA_LIMIT = 800
    RECOMMENDED_DEPOSIT_L2_GAS_LIMIT = 10000000
    L1_MESSENGER_ADDRESS = "0x0000000000000000000000000000000000008008"

    def __init__(self, zksync_web3: Web3, eth_web3: Web3, l1_account: BaseAccount):
        self._eth_web3 = eth_web3
        self._eth_web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self._zksync_web3 = zksync_web3
        self._main_contract_address = Web3.to_checksum_address(
            self._zksync_web3.zksync.zks_main_contract()
        )
        self.contract = self._eth_web3.eth.contract(
            self._main_contract_address, abi=zksync_abi_default()
        )
        self._l1_account = l1_account
        self.bridge_addresses: BridgeAddresses = (
            self._zksync_web3.zksync.zks_get_bridge_contracts()
        )

    @property
    def main_contract(self) -> Union[Type[Contract], Contract]:
        """Returns Contract wrapper of the zkSync smart contract."""
        return self.contract

    @property
    def address(self):
        """Returns the wallet address."""
        return self._l1_account.address

    def _get_withdraw_log(self, tx_receipt: TxReceipt, index: int = 0):
        topic = event_signature_to_log_topic("L1MessageSent(address,bytes32,bytes)")

        def impl_filter(log):
            return (
                log["address"] == self.L1_MESSENGER_ADDRESS
                and log["topics"][0] == topic
            )

        filtered_logs = list(filter(impl_filter, tx_receipt["logs"]))
        return filtered_logs[index], int(tx_receipt["l1BatchTxIndex"], 16)

    def _get_withdraw_l2_to_l1_log(self, tx_receipt: TxReceipt, index: int = 0):
        msgs = []
        for i, e in enumerate(tx_receipt["l2ToL1Logs"]):
            if e["sender"].lower() == self.L1_MESSENGER_ADDRESS.lower():
                msgs.append((i, e))
        l2_to_l1_log_index, log = msgs[index]
        return l2_to_l1_log_index, log

    def _finalize_withdrawal_params(self, withdraw_hash, index: int) -> dict:
        tx_receipt = self._zksync_web3.zksync.get_transaction_receipt(withdraw_hash)
        log, l1_batch_tx_id = self._get_withdraw_log(tx_receipt, index)
        l2_to_l1_log_index, _ = self._get_withdraw_l2_to_l1_log(tx_receipt, index)
        sender = add_0x_prefix(HexStr(log["topics"][1][12:].hex()))
        proof: ZksMessageProof = self._zksync_web3.zksync.zks_get_log_proof(
            withdraw_hash, l2_to_l1_log_index
        )
        bytes_data = to_bytes(log["data"])
        msg = self._zksync_web3.codec.decode(["bytes"], bytes_data)[0]
        l1_batch_number = int(log["l1BatchNumber"], 16)

        return {
            "l1_batch_number": l1_batch_number,
            "l2_message_index": proof.id,
            "l2_tx_number_in_block": l1_batch_tx_id,
            "message": msg,
            "sender": sender,
            "proof": proof.proof,
        }

    def get_l1_bridge_contracts(self) -> L1BridgeContracts:
        """Returns L1 bridge contract wrappers."""
        return L1BridgeContracts(
            erc20=self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(
                    self.bridge_addresses.erc20_l1_default_bridge
                ),
                abi=l1_bridge_abi_default(),
            ),
            weth=self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(self.bridge_addresses.weth_bridge_l1),
                abi=l1_bridge_abi_default(),
            ),
        )

    def get_l1_balance(
        self,
        token: HexStr = ADDRESS_DEFAULT,
        block: EthBlockParams = EthBlockParams.LATEST,
    ) -> int:
        """
        Returns the amount of the token the Wallet has on Ethereum.
        :param token: Token address. ETH by default.
        :param block: The block the balance should be checked on. committed, i.e. the latest processed one is the default option.
        """
        if is_eth(token):
            return self._eth_web3.eth.get_balance(self.address, block.value)
        else:
            token_contract = self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(token), abi=get_erc20_abi()
            )
            return token_contract.functions.balanceOf(self.address).call(
                {"chainId": self._eth_web3.eth.chain_id, "from": self.address}
            )

    def get_allowance_l1(self, token: HexStr, bridge_address: Address = None):
        """
        Returns the amount of approved tokens for a specific L1 bridge.

        :param token: The address of the token on L1.
        :param bridge_address: The address of the bridge contract to be used. Defaults to the default zkSync bridge (either L1EthBridge or L1Erc20Bridge).
        """
        token_contract = self._eth_web3.eth.contract(
            address=Web3.to_checksum_address(token), abi=get_erc20_abi()
        )
        if bridge_address is None:
            l2_weth_token = ADDRESS_DEFAULT
            try:
                l2_weth_token = (
                    self.get_l1_bridge_contracts()
                    .weth.functions.l2TokenAddress(token)
                    .call()
                )
            except:
                pass
            if l2_weth_token == ADDRESS_DEFAULT:
                bridge_address = self.bridge_addresses.erc20_l1_default_bridge
            else:
                bridge_address = self.bridge_addresses.weth_bridge_l1
        return token_contract.functions.allowance(self.address, bridge_address).call(
            {
                "chainId": self._eth_web3.eth.chain_id,
                "from": self.address,
            }
        )

    def l2_token_address(self, address: HexStr) -> HexStr:
        """
        Returns the L2 token address equivalent for a L1 token address as they are not equal. ETH's address is set to zero address.

        :param address: The address of the token on L1.
        """
        if is_eth(address):
            return ADDRESS_DEFAULT

        contracts = self.get_l1_bridge_contracts()
        try:
            l2_weth_token = contracts.weth.functions.l2TokenAddress(address).call()
            if l2_weth_token != ADDRESS_DEFAULT:
                return l2_weth_token
        except:
            pass
        return contracts.erc20.functions.l2TokenAddress(address).call()

    def approve_erc20(
        self,
        token: HexStr,
        amount: int,
        bridge_address: HexStr = None,
        gas_limit: int = None,
    ) -> TxReceipt:
        """
        Bridging ERC20 tokens from Ethereum requires approving the tokens to the zkSync Ethereum smart contract.

        :param token: The Ethereum address of the token.
        :param amount: The amount of the token to be approved.
        :param bridge_address: The address of the bridge contract to be used. Defaults to the default zkSync bridge (either L1EthBridge or L1Erc20Bridge).
        :param gas_limit:
        """
        if is_eth(token):
            raise RuntimeError(
                "ETH token can't be approved. The address of the token does not exist on L1"
            )

        erc20 = self._eth_web3.eth.contract(
            address=Web3.to_checksum_address(token), abi=get_erc20_abi()
        )

        if bridge_address is None:
            l2_weth_token = ADDRESS_DEFAULT
            try:
                l2_weth_token = (
                    self.get_l1_bridge_contracts()
                    .weth.functions.l2TokenAddress(token)
                    .call()
                )
            except:
                pass
            if l2_weth_token == ADDRESS_DEFAULT:
                bridge_address = self.bridge_addresses.erc20_l1_default_bridge
            else:
                bridge_address = self.bridge_addresses.weth_bridge_l1
        if gas_limit is None:
            # TODO: get the approve(bridgeAddress, amount) estimateGas transaction to put correct gas_limit
            gas_limit = RecommendedGasLimit.ERC20_APPROVE
        options = TransactionOptions(
            chain_id=self._eth_web3.eth.chain_id,
            gas_price=self._eth_web3.eth.gas_price,
            gas_limit=gas_limit,
            nonce=self._eth_web3.eth.get_transaction_count(self.address),
        )
        tx = erc20.functions.approve(bridge_address, amount).build_transaction(
            prepare_transaction_options(options, self.address)
        )
        signed_tx = self._l1_account.sign_transaction(tx)
        tx_hash = self._eth_web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self._eth_web3.eth.wait_for_transaction_receipt(tx_hash)

        return tx_receipt

    def get_base_cost(
        self,
        l2_gas_limit: int,
        gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT,
        gas_price: int = None,
    ):
        """
        Returns base cost for L2 transaction.

        :param l2_gas_limit: The gasLimit for the L2 contract call.
        :param gas_per_pubdata_byte: The L2 gas price for each published L1 calldata byte (optional).
        :param gas_price: The L1 gas price of the L1 transaction that will send the request for an execute call (optional).
        """
        if gas_price is None:
            gas_price = self._eth_web3.eth.gas_price
        options = TransactionOptions(
            chain_id=self._eth_web3.eth.chain_id,
            nonce=self._eth_web3.eth.get_transaction_count(self.address),
        )
        return self.contract.functions.l2TransactionBaseCost(
            gas_price, l2_gas_limit, gas_per_pubdata_byte
        ).call(prepare_transaction_options(options, self.address))

    def prepare_deposit_tx(self, transaction: DepositTransaction) -> DepositTransaction:
        """
        Returns populated deposit transaction.

        :param transaction: DepositTransaction class. Not optional arguments are token(L1 token address) and amount.
        """
        if transaction.options is None:
            transaction.options = TransactionOptions()
        if transaction.to is None:
            transaction.to = self.address
        if transaction.options.chain_id is None:
            transaction.options.chain_id = self._eth_web3.eth.chain_id
        if transaction.bridge_address is not None:
            bridge_contract = self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(transaction.bridge_address),
                abi=l1_bridge_abi_default(),
            )

            if transaction.custom_bridge_data is None:
                if transaction.bridge_address == self.bridge_addresses.weth_bridge_l1:
                    transaction.custom_bridge_data = "0x"
                else:
                    token_contract = self._zksync_web3.zksync.contract(
                        transaction.token, abi=get_erc20_abi()
                    )
                    transaction.custom_bridge_data = get_custom_bridge_data(
                        token_contract
                    )

            if transaction.l2_gas_limit is None:
                l2_address = bridge_contract.functions.l2TokenAddress(
                    transaction.token
                ).call()
                transaction.l2_gas_limit = self.estimate_custom_bridge_deposit_l2_gas(
                    transaction.bridge_address,
                    l2_address,
                    transaction.token,
                    transaction.amount,
                    transaction.to,
                    transaction.custom_bridge_data,
                    self.address,
                    transaction.gas_per_pubdata_byte,
                )
        elif transaction.l2_gas_limit is None:
            transaction.l2_gas_limit = self.estimate_default_bridge_deposit_l2_gas(
                transaction.token,
                transaction.amount,
                transaction.to,
                transaction.gas_per_pubdata_byte,
                self.address,
            )
        if (
            transaction.options.gas_price is None
            and transaction.options.max_fee_per_gas is None
        ):
            isReady, head = self.check_if_l1_chain_is_london_ready()
            if isReady:
                if transaction.options.max_priority_fee_per_gas is None:
                    transaction.options.max_priority_fee_per_gas = (
                        self._eth_web3.eth.max_priority_fee
                    )
                transaction.options.max_fee_per_gas = int(
                    ((head["baseFeePerGas"] * 3) / 2)
                    + transaction.options.max_priority_fee_per_gas
                )
        else:
            transaction.options.gas_price = self._eth_web3.eth.gas_price

        gas_price_for_estimation: int
        if transaction.options.max_priority_fee_per_gas is not None:
            gas_price_for_estimation = transaction.options.max_fee_per_gas
        else:
            gas_price_for_estimation = transaction.options.gas_price

        base_cost = self.get_base_cost(
            transaction.l2_gas_limit,
            transaction.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        if is_eth(transaction.token):
            transaction.options.value = (
                base_cost + transaction.operator_tip + transaction.amount
            )
        else:
            if transaction.refund_recipient is None:
                transaction.refund_recipient = ADDRESS_DEFAULT
            transaction.options.value = base_cost + transaction.operator_tip

        check_base_cost(base_cost, transaction.options.value)

        return transaction

    def get_full_required_deposit_fee(
        self, transaction: DepositTransaction
    ) -> FullDepositFee:
        """
        Retrieves the full needed ETH fee for the deposit. Returns the L1 fee and the L2 fee FullDepositFee(core/types.py).

        :param transaction: DepositTransaction: DepositTransaction class. Not optional argument is amount.
        """
        dummy_amount = 1

        if transaction.options is None:
            transaction.options = TransactionOptions()

        if transaction.to is None:
            transaction.to = self.address

        if transaction.bridge_address is not None:
            bridge_contract = self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(transaction.bridge_address),
                abi=l1_bridge_abi_default(),
            )

            if transaction.custom_bridge_data is None:
                if transaction.bridge_address == self.bridge_addresses.weth_bridge_l1:
                    transaction.custom_bridge_data = "0x"
                else:
                    token_contract = self._zksync_web3.zksync.contract(
                        transaction.token, abi=get_erc20_abi()
                    )
                    transaction.custom_bridge_data = get_custom_bridge_data(
                        token_contract
                    )

            if transaction.l2_gas_limit is None:
                l2_address = bridge_contract.functions.l2TokenAddress(
                    transaction.token
                ).call()
                transaction.l2_gas_limit = self.estimate_custom_bridge_deposit_l2_gas(
                    transaction.bridge_address,
                    l2_address,
                    transaction.token,
                    dummy_amount,
                    transaction.to,
                    transaction.custom_bridge_data,
                    self.address,
                    transaction.gas_per_pubdata_byte,
                )
        elif transaction.l2_gas_limit is None:
            transaction.l2_gas_limit = self.estimate_default_bridge_deposit_l2_gas(
                transaction.token,
                dummy_amount,
                transaction.to,
                transaction.gas_per_pubdata_byte,
                self.address,
            )
        if (
            transaction.options.gas_price is None
            and transaction.options.max_fee_per_gas is None
        ):
            isReady, head = self.check_if_l1_chain_is_london_ready()
            if isReady:
                if transaction.options.max_priority_fee_per_gas is None:
                    transaction.options.max_priority_fee_per_gas = (
                        self._eth_web3.eth.max_priority_fee
                    )
                transaction.options.max_fee_per_gas = int(
                    ((head["baseFeePerGas"] * 3) / 2)
                    + transaction.options.max_priority_fee_per_gas
                )
        else:
            transaction.options.gas_price = self._eth_web3.eth.gas_price

        gas_price_for_estimation: int
        if transaction.options.max_priority_fee_per_gas is not None:
            gas_price_for_estimation = transaction.options.max_fee_per_gas
        else:
            gas_price_for_estimation = transaction.options.gas_price

        base_cost = self.get_base_cost(
            transaction.l2_gas_limit,
            transaction.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        self_balance_eth = self.get_l1_balance()
        # We could use 0, because the final fee will anyway be bigger than
        if base_cost >= (self_balance_eth + dummy_amount):
            recommended_eth_balance = (
                RecommendedGasLimit.L1_RECOMMENDED_ETH_DEPOSIT_GAS_LIMIT
            )
            if not is_eth(transaction.token):
                recommended_eth_balance = (
                    RecommendedGasLimit.L1_RECOMMENDED_MIN_ERC_20_DEPOSIT_GAS_LIMIT
                )
            recommended_eth_balance = (
                recommended_eth_balance * gas_price_for_estimation + base_cost
            )

            RuntimeError(
                "Not enough balance for deposit. Under the provided gas price, "
                + f"the recommended balance to perform a deposit is ${recommended_eth_balance} ETH"
            )

        if not is_eth(transaction.token):
            allowance = self.get_allowance_l1(
                transaction.token, transaction.bridge_address
            )
            if allowance < dummy_amount:
                RuntimeError("Not enough allowance to cover the deposit")

        # Deleting the explicit gas limits in the fee estimation
        # in order to prevent the situation where the transaction
        # fails because the user does not have enough balance
        del transaction.options.gas_price
        del transaction.options.max_fee_per_gas
        del transaction.options.max_priority_fee_per_gas

        transaction.amount = dummy_amount
        l1_gas_limit = self.estimate_gas_deposit(transaction)

        full_cost: FullDepositFee = FullDepositFee(
            base_cost=base_cost,
            l1_gas_limit=l1_gas_limit,
            l2_gas_limit=transaction.l2_gas_limit,
        )
        if transaction.options.gas_price is not None:
            full_cost.gas_price = transaction.options.gas_price
        else:
            full_cost.max_priority_fee_per_gas = (
                transaction.options.max_priority_fee_per_gas
            )
            full_cost.max_fee_per_gas = transaction.options.max_fee_per_gas

        return full_cost

    def deposit(self, transaction: DepositTransaction):
        """
        Transfers the specified token from the associated account on the L1 network to the target account on the L2 network.
        The token can be either ETH or any ERC20 token. For ERC20 tokens,
        enough approved tokens must be associated with the specified L1 bridge (default one or the one defined in transaction.bridgeAddress).
        In this case, transaction.approveERC20 can be enabled to perform token approval.
        If there are already enough approved tokens for the L1 bridge, token approval will be skipped.
        To check the amount of approved tokens for a specific bridge, use the allowanceL1 method.

        :param transaction: DepositTransaction class. Not optional arguments are token(L1 token address) and amount.
        """
        transaction = self.prepare_deposit_tx(transaction)

        if is_eth(transaction.token):
            tx = deposit_to_request_execute(transaction)
            return self.request_execute(tx)
        else:
            if transaction.approve_erc20:
                self.approve_erc20(
                    transaction.token,
                    transaction.amount,
                    transaction.bridge_address,
                    transaction.options.gas_limit,
                )

            if transaction.bridge_address is not None:
                l1_bridge = self._eth_web3.eth.contract(
                    address=Web3.to_checksum_address(transaction.bridge_address),
                    abi=l1_bridge_abi_default(),
                )
            else:
                l2_weth_token = ADDRESS_DEFAULT
                try:
                    l2_weth_token = (
                        self.get_l1_bridge_contracts()
                        .weth.functions.l2TokenAddress(transaction.token)
                        .call()
                    )
                except:
                    pass
                if l2_weth_token == ADDRESS_DEFAULT:
                    bridge_address = self.bridge_addresses.erc20_l1_default_bridge
                else:
                    bridge_address = self.bridge_addresses.weth_bridge_l1
                l1_bridge = self._eth_web3.eth.contract(
                    address=Web3.to_checksum_address(bridge_address),
                    abi=l1_bridge_abi_default(),
                )
            if transaction.options.nonce is None:
                transaction.options.nonce = self._eth_web3.eth.get_transaction_count(
                    self.address
                )
            tx = l1_bridge.functions.deposit(
                transaction.to,
                transaction.token,
                transaction.amount,
                transaction.l2_gas_limit,
                transaction.gas_per_pubdata_byte,
                transaction.refund_recipient,
            ).build_transaction(
                {
                    "from": self.address,
                    "maxFeePerGas": transaction.options.max_fee_per_gas,
                    "maxPriorityFeePerGas": transaction.options.max_priority_fee_per_gas,
                    "nonce": self._eth_web3.eth.get_transaction_count(self.address),
                    "value": transaction.options.value,
                }
            )
            signed_tx = self._l1_account.sign_transaction(tx)
            txn_hash = self._eth_web3.eth.send_raw_transaction(signed_tx.rawTransaction)

            return txn_hash

    def estimate_gas_deposit(self, transaction: DepositTransaction):
        """
        Estimates the amount of gas required for a deposit transaction on L1 network.
        Gas of approving ERC20 token is not included in estimation.

        :param transaction: DepositTransaction class. Not optional arguments are token(L1 token address) and amount.
        """
        transaction = self.prepare_deposit_tx(transaction)
        if is_eth(transaction.token):
            tx = self.contract.functions.requestL2Transaction(
                Web3.to_checksum_address(transaction.to),
                transaction.l2_value,
                HexStr("0x"),
                transaction.l2_gas_limit,
                transaction.gas_per_pubdata_byte,
                list(),
                self.address,
            ).build_transaction(
                prepare_transaction_options(transaction.options, self.address)
            )

            return self._eth_web3.eth.estimate_gas(tx)
        else:
            if transaction.bridge_address is None:
                bridge = self.get_l1_bridge_contracts().erc20
            else:
                bridge = self._eth_web3.eth.contract(
                    Web3.to_checksum_address(transaction.bridge_address),
                    abi=get_erc20_abi(),
                )

            tx = bridge.functions.deposit(
                transaction.to,
                transaction.token,
                transaction.amount,
                transaction.l2_gas_limit,
                transaction.gas_per_pubdata_byte,
                self.address,
            ).build_transaction(
                prepare_transaction_options(transaction.options, self.address)
            )

            return self._eth_web3.eth.estimate_gas(tx)

    def claim_failed_deposit(self, deposit_hash: HexStr):
        """
        The claimFailedDeposit method withdraws funds from the initiated deposit, which failed when finalizing on L2.
        If the deposit L2 transaction has failed,
        it sends an L1 transaction calling claimFailedDeposit method of the L1 bridge,
        which results in returning L1 tokens back to the depositor, otherwise throws the error.

        :param deposit_hash: The L2 transaction hash of the failed deposit.
        """
        receipt = self._zksync_web3.zksync.eth_get_transaction_receipt(deposit_hash)
        success_log: L1ToL2Log
        success_log_index: int
        for i, log in enumerate(receipt.l2_to_l1_logs):
            if log.sender == BOOTLOADER_FORMAL_ADDRESS and log.key == deposit_hash:
                success_log_index = i
                success_log = log

        if success_log.value != ZkSyncAddresses.ETH_ADDRESS:
            raise RuntimeError("Cannot claim successful deposit")

        transaction = self._zksync_web3.zksync.eth_get_transaction_by_hash(deposit_hash)

        l1_bridge_address = undo_l1_to_l2_alias(receipt.from_)
        l1_bridge = self._eth_web3.eth.contract(
            address=Web3.to_checksum_address(l1_bridge_address),
            abi=l1_bridge_abi_default(),
        )

        l2_bridge = self._eth_web3.eth.contract(abi=l2_bridge_abi_default())
        calldata = l2_bridge.decode_function_input(transaction["data"])

        proof = self._zksync_web3.zksync.zks_get_log_proof(
            deposit_hash, success_log_index
        )
        if proof is None:
            raise RuntimeError("Log proof not found!")

        options = TransactionOptions(
            chain_id=self._eth_web3.eth.chain_id,
            nonce=self._eth_web3.eth.get_transaction_count(self.address),
        )
        return l1_bridge.functions.claimFailedDeposit(
            calldata[1]["_l1Sender"],
            calldata[1]["_l1Token"],
            to_bytes(deposit_hash),
            receipt.block_number,
            proof.id,
            receipt.l1_batch_tx_index,
            proof.proof,
        ).call(prepare_transaction_options(options, self.address))

    def estimate_default_bridge_deposit_l2_gas(
        self,
        token: HexStr,
        amount: int,
        to: HexStr,
        gas_per_pubdata_byte: int = None,
        from_: HexStr = None,
    ) -> int:
        if from_ is None:
            from_ = self._l1_account.address
        if gas_per_pubdata_byte is None:
            gas_per_pubdata_byte = DEPOSIT_GAS_PER_PUBDATA_LIMIT
        if is_eth(token):
            func_call = TxFunctionCall(
                to=to, from_=from_, value=amount, gas_per_pub_data=gas_per_pubdata_byte
            )
            return self._zksync_web3.zksync.zks_estimate_l1_to_l2_execute(func_call.tx)
        else:
            l2_weth_token = ADDRESS_DEFAULT
            try:
                l2_weth_token = (
                    self.get_l1_bridge_contracts()
                    .weth.functions.l2TokenAddress(token)
                    .call()
                )
            except:
                pass
            if l2_weth_token == ADDRESS_DEFAULT:
                value = 0
                l1_bridge_address = self.bridge_addresses.erc20_l1_default_bridge
                l2_bridge_address = self.bridge_addresses.erc20_l2_default_bridge
                token_contract = self._eth_web3.eth.contract(
                    Web3.to_checksum_address(token), abi=get_erc20_abi()
                )
                bridge_data = get_custom_bridge_data(token_contract)
            else:
                value = amount
                l1_bridge_address = self.bridge_addresses.weth_bridge_l1
                l2_bridge_address = self.bridge_addresses.weth_bridge_l2
                bridge_data = "0x"

            return self.estimate_custom_bridge_deposit_l2_gas(
                l1_bridge_address,
                l2_bridge_address,
                token,
                amount,
                to,
                bridge_data,
                from_,
                gas_per_pubdata_byte,
                value,
            )

    def estimate_custom_bridge_deposit_l2_gas(
        self,
        l1_bridge_address: HexStr,
        l2_bridge_address: HexStr,
        token: HexStr,
        amount: int,
        to: HexStr,
        bridge_data: bytes,
        from_: HexStr,
        gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT,
        value: int = 0,
    ) -> int:
        calldata = self.get_erc_20_call_data(token, from_, to, amount, bridge_data)
        tx = TxFunctionCall(
            from_=apply_l1_to_l2_alias(l1_bridge_address),
            to=l2_bridge_address,
            data=calldata,
            gas_per_pub_data=gas_per_pubdata_byte,
            value=value,
        )
        return self._zksync_web3.zksync.zks_estimate_l1_to_l2_execute(tx.tx)

    def get_erc_20_call_data(
        self,
        l1_token_address: HexStr,
        l1_sender: HexStr,
        l2_receiver: HexStr,
        amount: int,
        bridge_data: bytes,
    ) -> HexStr:
        l2_bridge = self._eth_web3.eth.contract(abi=l2_bridge_abi_default())
        return l2_bridge.encodeABI(
            "finalizeDeposit",
            (l1_sender, l2_receiver, l1_token_address, amount, bridge_data),
        )

    def finalize_withdrawal(self, withdraw_hash, index: int = 0):
        """
        Proves the inclusion of the L2 -> L1 withdrawal message.

        :param withdraw_hash: Hash of the L2 transaction where the withdrawal was initiated.
        :param index:nIn case there were multiple withdrawals in one transaction, you may pass an index of the withdrawal you want to finalize (defaults to 0).
        """
        params = self._finalize_withdrawal_params(withdraw_hash, index)
        merkle_proof = []
        for proof in params["proof"]:
            merkle_proof.append(to_bytes(proof))

        options = TransactionOptions(
            chain_id=self._eth_web3.eth.chain_id,
            nonce=self._eth_web3.eth.get_transaction_count(self.address),
        )

        if is_eth(params["sender"]):
            withdraw_to = HexStr("0x" + params["message"][4:24].hex())
            if withdraw_to.lower() == self.bridge_addresses.weth_bridge_l1.lower():
                tx = (
                    self.get_l1_bridge_contracts()
                    .weth.functions.finalizeEthWithdrawal(
                        params["l1_batch_number"],
                        params["l2_message_index"],
                        params["l2_tx_number_in_block"],
                        params["message"],
                        merkle_proof,
                    )
                    .build_transaction(
                        prepare_transaction_options(options, self.address)
                    )
                )
            else:
                tx = self.contract.functions.finalizeEthWithdrawal(
                    params["l1_batch_number"],
                    params["l2_message_index"],
                    params["l2_tx_number_in_block"],
                    params["message"],
                    merkle_proof,
                ).build_transaction(prepare_transaction_options(options, self.address))
            signed = self._l1_account.sign_transaction(tx)
            tx_hash = self._eth_web3.eth.send_raw_transaction(signed.rawTransaction)
            return tx_hash
        else:
            l2_bridge = self._zksync_web3.zksync.contract(
                address= Web3.to_checksum_address(params["sender"]), abi=l2_bridge_abi_default()
            )
            l1_bridge = self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(l2_bridge.functions.l1Bridge().call()),
                abi=l1_bridge_abi_default(),
            )
            l1_batch_number = params["l1_batch_number"]
            l2_message_index = params["l2_message_index"]
            l2_tx_number_in_block = params["l2_tx_number_in_block"]
            message = params["message"]

            tx = l1_bridge.functions.finalizeWithdrawal(
                params["l1_batch_number"],
                params["l2_message_index"],
                params["l2_tx_number_in_block"],
                params["message"],
                merkle_proof,
            ).build_transaction(prepare_transaction_options(options, self.address))

            signed = self._l1_account.sign_transaction(tx)
            tx_hash = self._eth_web3.eth.send_raw_transaction(signed.rawTransaction)
            return tx_hash

    def is_withdrawal_finalized(self, withdraw_hash, index: int = 0):
        """
        Checks if withdraw is finalized from L2 -> L1

        :param withdraw_hash: Hash of the L2 transaction where the withdrawal was initiated.
        :param index:nIn case there were multiple withdrawals in one transaction, you may pass an index of the withdrawal you want to finalize (defaults to 0).
        """
        tx_receipt = self._zksync_web3.zksync.get_transaction_receipt(withdraw_hash)
        log, _ = self._get_withdraw_log(tx_receipt, index)
        l2_to_l1_log_index, _ = self._get_withdraw_l2_to_l1_log(tx_receipt, index)
        sender = add_0x_prefix(HexStr(log["topics"][1][12:].hex()))
        hex_hash = withdraw_hash
        proof: ZksMessageProof = self._zksync_web3.zksync.zks_get_log_proof(
            hex_hash, l2_to_l1_log_index
        )

        l2_block_number = log["l1BatchNumber"]
        options = TransactionOptions(
            chain_id=self._eth_web3.eth.chain_id,
            nonce=self._eth_web3.eth.get_transaction_count(self.address),
        )
        if is_eth(sender):
            return self.contract.functions.isEthWithdrawalFinalized(
                int(l2_block_number, 16), proof.id
            ).call(prepare_transaction_options(options, self.address))
        else:
            l1_bridge = self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(
                    self.bridge_addresses.erc20_l1_default_bridge
                ),
                abi=l1_bridge_abi_default(),
            )
            return l1_bridge.functions.isWithdrawalFinalized(
                int(l2_block_number, 16), proof.id
            ).call()

    def request_execute(self, transaction: RequestExecuteCallMsg):
        """
        Request execution of L2 transaction from L1.

        :param transaction: RequestExecuteCallMsg class, required parameters are:
            contract_address(L2 contract to be called) and call_data (the input of the L2 transaction).
            Example: RequestExecuteCallMsg(
                contract_address=Web3.to_checksum_address(
                    zksync.zksync.main_contract_address
                ),
                call_data=HexStr("0x"),
                l2_value=amount,
                l2_gas_limit=900_000,
            )
        """
        transaction = self.get_request_execute_transaction(transaction)
        tx = self.contract.functions.requestL2Transaction(
            transaction.contract_address,
            transaction.l2_value,
            transaction.call_data,
            transaction.l2_gas_limit,
            transaction.gas_per_pubdata_byte,
            transaction.factory_deps,
            transaction.refund_recipient,
        ).build_transaction(
            prepare_transaction_options(transaction.options, transaction.from_)
        )
        signed_tx = self._l1_account.sign_transaction(tx)
        tx_hash = self._eth_web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return tx_hash

    def check_if_l1_chain_is_london_ready(self):
        head = self._eth_web3.eth.get_block("latest")
        if head["baseFeePerGas"] is not None:
            return True, head
        return False, head

    def get_request_execute_transaction(
        self, transaction: RequestExecuteCallMsg
    ) -> RequestExecuteCallMsg:
        """
        Returns populated deposit transaction.

        :param transaction: RequestExecuteCallMsg class, required parameters are:
            contract_address(L2 contract to be called) and call_data (the input of the L2 transaction).
        """
        if transaction.options is None:
            transaction.options = TransactionOptions()
        if transaction.factory_deps is None:
            transaction.factory_deps = list()
        if transaction.refund_recipient is None:
            transaction.refund_recipient = self.address
        if transaction.from_ is None:
            transaction.from_ = self.address
        if transaction.options.nonce is None:
            transaction.options.nonce = self._eth_web3.eth.get_transaction_count(
                self.address
            )
        if transaction.l2_gas_limit == 0:
            meta = EIP712Meta(
                gas_per_pub_data=transaction.gas_per_pubdata_byte,
                factory_deps=transaction.factory_deps,
            )
            transaction.l2_gas_limit = (
                self._zksync_web3.zksync.zks_estimate_l1_to_l2_execute(
                    {
                        "from": transaction.from_,
                        "to": transaction.contract_address,
                        "eip712Meta": meta,
                    }
                )
            )
        if (
            transaction.options.gas_price is None
            and transaction.options.max_fee_per_gas is None
        ):
            isReady, head = self.check_if_l1_chain_is_london_ready()
            if isReady:
                if transaction.options.max_priority_fee_per_gas is None:
                    transaction.options.max_priority_fee_per_gas = (
                        self._eth_web3.eth.max_priority_fee
                    )
                transaction.options.max_fee_per_gas = int(
                    ((head["baseFeePerGas"] * 3) / 2)
                    + transaction.options.max_priority_fee_per_gas
                )
        else:
            transaction.options.gas_price = self._eth_web3.eth.gas_price

        gas_price_for_estimation: int
        if transaction.options.max_priority_fee_per_gas is not None:
            gas_price_for_estimation = transaction.options.max_fee_per_gas
        else:
            gas_price_for_estimation = transaction.options.gas_price

        base_cost = self.get_base_cost(
            transaction.l2_gas_limit,
            transaction.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        if transaction.options.value is None:
            transaction.options.value = (
                base_cost + transaction.operator_tip + transaction.l2_value
            )

        check_base_cost(base_cost, transaction.options.value)

        return transaction

    def estimate_gas_request_execute(self, transaction: RequestExecuteCallMsg) -> int:
        """
        Estimates the amount of gas required for a request execute transaction.

        :param transaction: RequestExecuteCallMsg class, required parameters are:
            contract_address(L2 contract to be called) and call_data (the input of the L2 transaction).
        """
        transaction = self.get_request_execute_transaction(transaction)
        tx = self.contract.functions.requestL2Transaction(
            Web3.to_checksum_address(transaction.contract_address),
            transaction.l2_value,
            transaction.call_data,
            transaction.l2_gas_limit,
            transaction.gas_per_pubdata_byte,
            transaction.factory_deps,
            transaction.refund_recipient,
        ).build_transaction(
            prepare_transaction_options(transaction.options, self.address)
        )

        return self._eth_web3.eth.estimate_gas(tx)