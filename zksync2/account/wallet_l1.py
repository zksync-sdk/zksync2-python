from typing import Union, Type

from eth_abi import encode
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
    ETH_ADDRESS_IN_CONTRACTS,
    LEGACY_ETH_ADDRESS,
    scale_gas_limit,
    is_address_eq,
)
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.utils import (
    zksync_abi_default,
    l1_bridge_abi_default,
    get_erc20_abi,
    l2_bridge_abi_default,
    l1_shared_bridge_abi_default,
    bridgehub_abi_default, get_zksync_hyperchain, l2_shared_bridge_abi_default,
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
            self._main_contract_address, abi=get_zksync_hyperchain()
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

    def get_bridgehub_contract(self) -> Union[Type[Contract], Contract]:
        """Returns Contract wrapper of the bridgehub smart contract."""
        address = self._zksync_web3.zksync.zks_get_bridgehub_contract_address()

        return self._eth_web3.eth.contract(
            address=Web3.to_checksum_address(address), abi=bridgehub_abi_default()
        )

    def get_l1_bridge_contracts(self) -> L1BridgeContracts:
        """Returns L1 bridge contract wrappers."""
        return L1BridgeContracts(
            erc20=self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(
                    self.bridge_addresses.erc20_l1_default_bridge
                ),
                abi=l1_bridge_abi_default(),
            ),
            shared=self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(
                    self.bridge_addresses.shared_l1_default_bridge
                ),
                abi=l1_shared_bridge_abi_default(),
            ),
            weth=self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(self.bridge_addresses.weth_bridge_l1),
                abi=l1_bridge_abi_default(),
            ),
        )

    def get_base_token(self) -> HexStr:
        """Returns the address of the base token on L1."""

        bridgehub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.eth.chain_id

        return bridgehub.functions.baseToken(chain_id).call()

    def is_eth_based_chain(self) -> bool:
        """Returns whether the chain is ETH-based."""
        return self._zksync_web3.zksync.is_eth_based_chain()

    def get_l1_balance(
        self,
        token: HexStr = ADDRESS_DEFAULT,
        block: EthBlockParams = EthBlockParams.LATEST,
    ) -> int:
        """
        Returns the amount of the token the Wallet has on Ethereum.
        :param token: Token address. ETH by default.
        :param block: The block the balance should be checked on. committed,
            i.e. the latest processed one is the default option.
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
        :param bridge_address: The address of the bridge contract to be used.
            Defaults to the default zkSync bridge (either L1EthBridge or L1Erc20Bridge).
        """
        token_contract = self._eth_web3.eth.contract(
            address=Web3.to_checksum_address(token), abi=get_erc20_abi()
        )
        if bridge_address is None:
            bridge_contracts = self.get_l1_bridge_contracts()
            bridge_address = bridge_contracts.shared.address
        return token_contract.functions.allowance(self.address, bridge_address).call(
            {
                "chainId": self._eth_web3.eth.chain_id,
                "from": self.address,
            }
        )

    def l2_token_address(self, address: HexStr) -> HexStr:
        """
        Returns the L2 token address equivalent for a L1 token address as they are not necessarily equal.
        The ETH address is set to the zero address.

        :param address: The address of the token on L1.
        """
        return self._zksync_web3.zksync.l2_token_address(address)

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
        :param bridge_address: The address of the bridge contract to be used.
            Defaults to the default zkSync bridge (either L1EthBridge or L1Erc20Bridge).
        :param gas_limit:
        """
        if is_eth(token):
            raise RuntimeError(
                "ETH token can't be approved. The address of the token does not exist on L1"
            )

        erc20 = self._eth_web3.eth.contract(
            address=Web3.to_checksum_address(token), abi=get_erc20_abi()
        )
        base_token = self.get_base_token()
        is_eth_based_chain = self.is_eth_based_chain()

        if bridge_address is None:
            if is_eth_based_chain is False and token.lower() == base_token.lower():
                bridge_address = (
                    self.get_bridgehub_contract().functions.sharedBridge().call()
                )
            else:
                bridge_contracts = self.get_l1_bridge_contracts()
                bridge_address = bridge_contracts.shared.address
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
        bridge_hub = self.get_bridgehub_contract()
        if gas_price is None:
            gas_price = self._eth_web3.eth.gas_price
        options = TransactionOptions(
            chain_id=self._eth_web3.eth.chain_id,
            nonce=self._eth_web3.eth.get_transaction_count(self.address),
        )
        return bridge_hub.functions.l2TransactionBaseCost(
            self._zksync_web3.eth.chain_id,
            gas_price,
            l2_gas_limit,
            gas_per_pubdata_byte,
        ).call(prepare_transaction_options(options, self.address))

    def get_deposit_allowance_params(self, token: HexStr, amount: int):
        if is_address_eq(token, LEGACY_ETH_ADDRESS):
            token = ETH_ADDRESS_IN_CONTRACTS

        base_token_address = self.get_base_token()
        is_eth_based_chain = self.is_eth_based_chain()

        if is_eth_based_chain and is_address_eq(token, ETH_ADDRESS_IN_CONTRACTS):
            raise RuntimeError(
                "ETH token can't be approved! The address of the token does not exist on L1."
            )
        elif is_address_eq(base_token_address, ETH_ADDRESS_IN_CONTRACTS):
            return [{"token": token, "allowance": amount}]
        elif is_address_eq(token, ETH_ADDRESS_IN_CONTRACTS):
            mint_value = self._get_deposit_mint_value_eth_on_non_eth_based_chain_tx(
                DepositTransaction(token=token, amount=amount)
            )
            return [{"token": base_token_address, "allowance": mint_value}]
        elif is_address_eq(token, base_token_address):
            _, mint_value = self._get_deposit_base_token_on_non_eth_based_chain_tx(
                DepositTransaction(token=token, amount=amount)
            )
            return [{"token": base_token_address, "allowance": mint_value}]
        # A deposit of a non-base token to a non-ETH-based chain requires two approvals.
        base_token_mint = (
            self._get_deposit_mint_value_non_base_token_to_non_eth_based_chain_tx(
                DepositTransaction(token=token, amount=amount)
            )
        )
        return [
            {"token": base_token_address, "allowance": base_token_mint},
            {"token": token, "allowance": amount},
        ]

    def _deposit_non_base_token_to_non_eth_based_chain(
        self, transaction: DepositTransaction
    ):
        tx, _ = self._get_deposit_non_base_token_to_non_eth_based_chain_tx(transaction)

        if transaction.options.gas_limit is None:
            tx["gas"] = scale_gas_limit(tx["gas"])

        signed_tx = self._l1_account.sign_transaction(tx)
        txn_hash = self._eth_web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return txn_hash

    def _deposit_base_token_to_non_eth_based_chain(
        self, transaction: DepositTransaction
    ):
        nonce = transaction.options.nonce if transaction.options is not None else None
        bridge_hub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        base_token_address = bridge_hub.functions.baseToken(chain_id).call()
        bridge_contracts = self.get_l1_bridge_contracts()

        tx, mint_value = self._get_deposit_base_token_on_non_eth_based_chain_tx(
            transaction
        )

        if transaction.approve_erc20 or transaction.approve_base_erc20:
            approve_options = (
                transaction.approve_base_options
                if transaction.approve_base_options is not None
                else transaction.approve_options
            )
            allowance = self.get_allowance_l1(
                base_token_address, bridge_contracts.shared.address
            )

            if approve_options is None:
                approve_options = TransactionOptions()

            if allowance < mint_value:
                approve_tx = self.approve_erc20(
                    base_token_address,
                    mint_value,
                    bridge_contracts.shared.address,
                    approve_options.gas_limit,
                )
                if nonce is None:
                    tx.options.nonce = self._eth_web3.eth.get_transaction_count(
                        self.address
                    )

        if tx.options.gas_limit is None:
            base_gas_limit = self.estimate_gas_request_execute(tx)
            tx.options.gas_limit = scale_gas_limit(base_gas_limit)

        return self.request_execute(tx)

    def _deposit_eth_to_non_eth_based_chain(self, transaction: DepositTransaction):
        tx, _ = self._get_deposit_eth_on_non_eth_based_chain_tx(transaction)

        if transaction.options.gas_limit is None:
            tx["gas"] = scale_gas_limit(tx["gas"])

        signed_tx = self._l1_account.sign_transaction(tx)
        txn_hash = self._eth_web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return txn_hash

    def _deposit_token_to_eth_based_chain(self, transaction: DepositTransaction):
        tx = self._get_deposit_token_on_eth_based_chain_tx(transaction)

        if transaction.options.gas_limit is None:
            base_gas_limit = self._eth_web3.eth.estimate_gas(tx)
            tx["gas"] = scale_gas_limit(base_gas_limit)

        signed_tx = self._l1_account.sign_transaction(tx)
        txn_hash = self._eth_web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return txn_hash

    def _deposit_eth_to_eth_based_chain(self, transaction: DepositTransaction):
        tx = self._get_deposit_eth_on_eth_based_chain_tx(transaction)

        if tx.options.gas_limit is None:
            base_gas_limit = self.estimate_gas_request_execute(tx)
            tx.options.gas_limit = scale_gas_limit(base_gas_limit)

        return self.request_execute(tx)

    def prepare_deposit_tx(self, transaction: DepositTransaction):
        """
        Returns populated deposit transaction.

        :param transaction: DepositTransaction class. Not optional arguments are token(L1 token address) and amount.
        """
        if transaction.token.lower() == LEGACY_ETH_ADDRESS:
            transaction.token = ETH_ADDRESS_IN_CONTRACTS

        bridge_hub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        base_token_address = bridge_hub.functions.baseToken(chain_id).call()
        is_eth_base_chain = base_token_address == ETH_ADDRESS_IN_CONTRACTS

        if is_eth_base_chain and is_address_eq(
            transaction.token, ETH_ADDRESS_IN_CONTRACTS
        ):
            return self._get_deposit_eth_on_eth_based_chain_tx(transaction)
        elif is_eth_base_chain:
            return self._get_deposit_token_on_eth_based_chain_tx(transaction)
        elif is_address_eq(transaction.token, ETH_ADDRESS_IN_CONTRACTS):
            tx, _ = self._get_deposit_eth_on_non_eth_based_chain_tx(transaction)
            return tx
        elif is_address_eq(transaction.token, base_token_address):
            tx, _ = self._get_deposit_base_token_on_non_eth_based_chain_tx(transaction)
            return tx
        else:
            tx, _ = self._get_deposit_non_base_token_to_non_eth_based_chain_tx(
                transaction
            )
            return tx

    def _get_deposit_mint_value_non_base_token_to_non_eth_based_chain_tx(
        self, transaction: DepositTransaction
    ):
        tx = self._get_deposit_tx_with_defaults(transaction)

        gas_price_for_estimation: int
        if tx.options.max_priority_fee_per_gas is not None:
            gas_price_for_estimation = tx.options.max_fee_per_gas
        else:
            gas_price_for_estimation = tx.options.gas_price

        base_cost = self.get_base_cost(
            tx.l2_gas_limit,
            tx.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )
        mint_value = base_cost + tx.operator_tip
        check_base_cost(base_cost, mint_value)

        return mint_value

    def _get_deposit_non_base_token_to_non_eth_based_chain_tx(
        self, transaction: DepositTransaction
    ):
        nonce = transaction.options.nonce if transaction.options is not None else None
        bridge_hub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        bridge_contracts = self.get_l1_bridge_contracts()
        base_token_address = bridge_hub.functions.baseToken(chain_id).call()

        tx = self._get_deposit_tx_with_defaults(transaction)

        mint_value = (
            self._get_deposit_mint_value_non_base_token_to_non_eth_based_chain_tx(tx)
        )
        tx.options.value = tx.options.value or 0

        if transaction.approve_base_erc20:
            allowance = self.get_allowance_l1(
                base_token_address, bridge_contracts.shared.address
            )

            if transaction.approve_base_options is None:
                transaction.approve_base_options = TransactionOptions()

            if allowance < mint_value:
                approve_tx = self.approve_erc20(
                    base_token_address,
                    mint_value,
                    bridge_contracts.shared.address,
                    transaction.approve_base_options.gas_limit,
                )
                if nonce is None:
                    tx.options.nonce = self._eth_web3.eth.get_transaction_count(
                        self.address
                    )

        if transaction.approve_erc20:
            bridge_address = (
                transaction.bridge_address
                if transaction.bridge_address is not None
                else bridge_contracts.shared.address
            )
            allowance = self.get_allowance_l1(transaction.token, bridge_address)

            if transaction.approve_options is None:
                transaction.approve_options = TransactionOptions()

            if allowance < transaction.amount:
                approve_tx = self.approve_erc20(
                    base_token_address,
                    transaction.amount,
                    bridge_address,
                    transaction.approve_options.gas_limit,
                )
                if nonce is None:
                    tx.options.nonce = self._eth_web3.eth.get_transaction_count(
                        self.address
                    )

        transaction_data = {
            "chainId": chain_id,
            "mintValue": mint_value,
            "l2Value": 0,
            "l2GasLimit": transaction.l2_gas_limit,
            "l2GasPerPubdataByteLimit": transaction.gas_per_pubdata_byte,
            "refundRecipient": transaction.refund_recipient or self.address,
            "secondBridgeAddress": bridge_contracts.shared.address,
            "secondBridgeValue": 0,
            "secondBridgeCalldata": encode(
                ["address", "uint256", "address"], [tx.token, tx.amount, tx.to]
            ),
        }

        return (
            bridge_hub.functions.requestL2TransactionTwoBridges(
                transaction_data
            ).build_transaction(
                prepare_transaction_options(tx.options, self.address, self._eth_web3)
            ),
            mint_value,
        )

    def _get_deposit_base_token_on_non_eth_based_chain_tx(
        self, transaction: DepositTransaction
    ):
        tx = self._get_deposit_tx_with_defaults(transaction)

        gas_price_for_estimation: int
        if tx.options.max_priority_fee_per_gas is not None:
            gas_price_for_estimation = tx.options.max_fee_per_gas
        else:
            gas_price_for_estimation = tx.options.gas_price

        base_cost = self.get_base_cost(
            tx.l2_gas_limit,
            tx.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        tx.options.value = 0

        return (
            RequestExecuteCallMsg(
                contract_address=tx.to,
                call_data=HexStr("0x"),
                mint_value=base_cost + tx.operator_tip + tx.amount,
                l2_value=tx.amount,
                operator_tip=tx.operator_tip,
                l2_gas_limit=tx.l2_gas_limit,
                gas_per_pubdata_byte=tx.gas_per_pubdata_byte,
                options=tx.options,
            ),
            base_cost + tx.operator_tip + tx.amount,
        )

    def _get_deposit_mint_value_eth_on_non_eth_based_chain_tx(
        self, tx: DepositTransaction
    ):
        tx = self._get_deposit_tx_with_defaults(tx)

        gas_price_for_estimation: int
        if tx.options.max_priority_fee_per_gas is not None:
            gas_price_for_estimation = tx.options.max_fee_per_gas
        else:
            gas_price_for_estimation = tx.options.gas_price

        base_cost = self.get_base_cost(
            tx.l2_gas_limit,
            tx.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        mint_value = base_cost + tx.operator_tip
        check_base_cost(base_cost, mint_value)

        return mint_value

    def _get_deposit_eth_on_non_eth_based_chain_tx(
        self, transaction: DepositTransaction
    ):
        nonce = transaction.options.nonce if transaction.options is not None else None
        bridge_hub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        shared_bridge = self.get_l1_bridge_contracts().shared
        base_token_address = bridge_hub.functions.baseToken(chain_id).call()

        tx = self._get_deposit_tx_with_defaults(transaction)
        mint_value = self._get_deposit_mint_value_eth_on_non_eth_based_chain_tx(tx)
        tx.options.value = tx.options.value or tx.amount

        if transaction.approve_base_erc20:
            allowance = self.get_allowance_l1(
                Web3.to_checksum_address(base_token_address), shared_bridge.address
            )

            if transaction.approve_base_options is None:
                transaction.approve_base_options = TransactionOptions()

            if allowance < mint_value:
                approve_tx = self.approve_erc20(
                    base_token_address,
                    mint_value,
                    shared_bridge.address,
                    transaction.approve_base_options.gas_limit,
                )
                if nonce is None:
                    tx.options.nonce = self._eth_web3.eth.get_transaction_count(
                        self.address
                    )

        transaction_data = {
            "chainId": chain_id,
            "mintValue": mint_value,
            "l2Value": 0,
            "l2GasLimit": transaction.l2_gas_limit,
            "l2GasPerPubdataByteLimit": transaction.gas_per_pubdata_byte,
            "refundRecipient": transaction.refund_recipient,
            "secondBridgeAddress": shared_bridge.address,
            "secondBridgeValue": transaction.amount,
            "secondBridgeCalldata": encode(
                ["address", "uint256", "address"], [ETH_ADDRESS_IN_CONTRACTS, 0, tx.to]
            ),
        }

        return (
            bridge_hub.functions.requestL2TransactionTwoBridges(
                transaction_data
            ).build_transaction(
                prepare_transaction_options(tx.options, self.address, self._eth_web3)
            ),
            mint_value,
        )

    def _get_deposit_token_on_eth_based_chain_tx(self, transaction: DepositTransaction):
        nonce = transaction.options.nonce if transaction.options is not None else None
        bridge_hub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        bridge_contracts = self.get_l1_bridge_contracts()

        tx = self._get_deposit_tx_with_defaults(transaction)

        if transaction.approve_erc20:
            proposed_bridge = bridge_contracts.shared.address
            bridge_address = (
                transaction.bridge_address
                if transaction.bridge_address is not None
                else proposed_bridge
            )

            allowance = self.get_allowance_l1(
                Web3.to_checksum_address(transaction.token), bridge_address
            )

            if transaction.approve_options is None:
                transaction.approve_options = TransactionOptions()

            if allowance < transaction.amount:
                approve_tx = self.approve_erc20(
                    transaction.token,
                    transaction.amount,
                    bridge_contracts.shared.address,
                    transaction.approve_options.gas_limit,
                )
                if nonce is None:
                    tx.options.nonce = self._eth_web3.eth.get_transaction_count(
                        self.address
                    )

        gas_price_for_estimation: int
        if tx.options.max_priority_fee_per_gas is not None:
            gas_price_for_estimation = tx.options.max_fee_per_gas
        else:
            gas_price_for_estimation = tx.options.gas_price

        base_cost = self.get_base_cost(
            tx.l2_gas_limit,
            tx.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        mint_value = base_cost + tx.operator_tip
        tx.options.value = tx.options.value or mint_value
        check_base_cost(base_cost, mint_value)

        second_bridge_address: str
        second_bridge_calldata: bytes
        if tx.bridge_address is not None:
            second_bridge_address = tx.bridge_address
            token_contract = self._eth_web3.eth.contract(
                address=Web3.to_checksum_address(tx.token), abi=get_erc20_abi()
            )
            second_bridge_calldata = get_custom_bridge_data(token_contract)
        else:
            second_bridge_address = self.get_l1_bridge_contracts().shared.address
            second_bridge_calldata = encode(
                ["address", "uint256", "address"], [tx.token, tx.amount, tx.to]
            )

        transaction_data = {
            "chainId": chain_id,
            "mintValue": mint_value,
            "l2Value": transaction.l2_value,
            "l2GasLimit": transaction.l2_gas_limit,
            "l2GasPerPubdataByteLimit": transaction.gas_per_pubdata_byte,
            "refundRecipient": transaction.refund_recipient,
            "secondBridgeAddress": second_bridge_address,
            "secondBridgeValue": 0,
            "secondBridgeCalldata": second_bridge_calldata,
        }

        return bridge_hub.functions.requestL2TransactionTwoBridges(
            transaction_data
        ).build_transaction(prepare_transaction_options(tx.options, self.address))

    def _get_deposit_eth_on_eth_based_chain_tx(self, transaction: DepositTransaction):
        tx = self._get_deposit_tx_with_defaults(transaction)

        gas_price_for_estimation: int
        if tx.options.max_priority_fee_per_gas is not None:
            gas_price_for_estimation = tx.options.max_fee_per_gas
        else:
            gas_price_for_estimation = tx.options.gas_price

        base_cost = self.get_base_cost(
            tx.l2_gas_limit,
            tx.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        tx.options.value = (
            base_cost + tx.operator_tip + tx.amount
            if tx.options.value is None
            else tx.options.value
        )

        return RequestExecuteCallMsg(
            contract_address=tx.to,
            call_data=HexStr("0x"),
            mint_value=tx.options.value,
            l2_value=tx.amount,
            operator_tip=tx.operator_tip,
            l2_gas_limit=tx.l2_gas_limit,
            gas_per_pubdata_byte=tx.gas_per_pubdata_byte,
            options=tx.options,
            refund_recipient=tx.refund_recipient,
        )

    def _get_deposit_tx_with_defaults(self, transaction: DepositTransaction):
        if transaction.options is None:
            transaction.options = TransactionOptions()
        if transaction.to is None:
            transaction.to = self.address
        if transaction.options.chain_id is None:
            transaction.options.chain_id = self._eth_web3.eth.chain_id
        if transaction.l2_gas_limit is None:
            transaction.l2_gas_limit = self._get_l2_gas_limit(transaction)
        if transaction.refund_recipient is None:
            transaction.refund_recipient = self.address
        if transaction.options.nonce is None:
            transaction.options.nonce = self._eth_web3.eth.get_transaction_count(
                self.address
            )
        self.insert_gas_price_in_transaction_options(transaction.options)

        return transaction

    def _get_l2_gas_limit(self, transaction: DepositTransaction):
        if transaction.bridge_address is not None:
            return self._get_l2_gas_limit_from_custom_bridge(transaction)

        return self.estimate_default_bridge_deposit_l2_gas(
            transaction.token,
            transaction.amount,
            transaction.to,
            transaction.gas_per_pubdata_byte,
            self.address,
        )

    def _get_l2_gas_limit_from_custom_bridge(self, transaction: DepositTransaction):
        if transaction.custom_bridge_data is None:
            token_contract = self._zksync_web3.zksync.contract(
                transaction.token, abi=get_erc20_abi()
            )
            transaction.custom_bridge_data = get_custom_bridge_data(token_contract)

        bridge = self._zksync_web3.zksync.contract(
            transaction.bridge_address, abi=l1_bridge_abi_default()
        )

        if transaction.options.chain_id is None:
            transaction.options.chain_id = self._eth_web3.eth.chain_id

        l2_address = bridge.functions.l2TokenAddress(transaction.token).call()

        return self.estimate_custom_bridge_deposit_l2_gas(
            transaction.bridge_address,
            l2_address,
            transaction.token,
            transaction.amount,
            transaction.to,
            transaction.custom_bridge_data,
            self.address,
            transaction.gas_per_pubdata_byte,
        )

    def get_full_required_deposit_fee(
        self, transaction: DepositTransaction
    ) -> FullDepositFee:
        """
        Retrieves the full needed ETH fee for the deposit.
        Returns the L1 fee and the L2 fee FullDepositFee(core/types.py).

        :param transaction: DepositTransaction: DepositTransaction class. Not optional argument is amount.
        """
        if is_address_eq(transaction.token, LEGACY_ETH_ADDRESS):
            transaction.token = ETH_ADDRESS_IN_CONTRACTS
        dummy_amount = 1
        transaction.amount = dummy_amount
        bridge_hub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        base_token_address = bridge_hub.functions.baseToken(chain_id).call()
        is_eth_based_chain = is_address_eq(base_token_address, ETH_ADDRESS_IN_CONTRACTS)

        tx = self._get_deposit_tx_with_defaults(transaction)

        gas_price_for_estimation = (
            tx.options.max_fee_per_gas
            if tx.options.max_fee_per_gas is not None
            else tx.options.gas_price
        )

        base_cost = self.get_base_cost(
            tx.l2_gas_limit,
            tx.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        if is_eth_based_chain:
            self_balance_eth = self.get_l1_balance()
            # We could use 0, because the final fee will anyway be bigger than
            if base_cost >= (self_balance_eth + dummy_amount):
                recommended_eth_balance = (
                    RecommendedGasLimit.L1_RECOMMENDED_ETH_DEPOSIT_GAS_LIMIT
                )
                if not is_address_eq(tx.token, LEGACY_ETH_ADDRESS):
                    recommended_eth_balance = (
                        RecommendedGasLimit.L1_RECOMMENDED_MIN_ERC_20_DEPOSIT_GAS_LIMIT
                    )

                RuntimeError(
                    "Not enough balance for deposit. Under the provided gas price, "
                    + f"the recommended balance to perform a deposit is ${recommended_eth_balance} ETH"
                )
            if (
                not is_address_eq(tx.token, ETH_ADDRESS_IN_CONTRACTS)
                and self.get_allowance_l1(tx.token, tx.bridge_address) < dummy_amount
            ):
                RuntimeError("Not enough allowance to cover the deposit!")
        else:
            mint_value = base_cost + tx.operator_tip
            if self.get_allowance_l1(base_token_address) < mint_value:
                RuntimeError("Not enough base token allowance to cover the deposit!")
            if is_address_eq(tx.token, ETH_ADDRESS_IN_CONTRACTS) or is_address_eq(
                tx.token, base_token_address
            ):
                tx.options.value = tx.amount
            else:
                tx.options.value = 0 if tx.options.value is None else tx.options.value
                if self.get_allowance_l1(tx.token) < dummy_amount:
                    RuntimeError("Not enough token allowance to cover the deposit!")

        full_cost: FullDepositFee = FullDepositFee(
            base_cost=base_cost,
            l1_gas_limit=0,
            l2_gas_limit=transaction.l2_gas_limit,
        )
        if tx.options.gas_price is not None:
            full_cost.gas_price = tx.options.gas_price
        else:
            full_cost.max_priority_fee_per_gas = tx.options.max_priority_fee_per_gas
            full_cost.max_fee_per_gas = tx.options.max_fee_per_gas

        # Deleting the explicit gas limits in the fee estimation
        # in order to prevent the situation where the transaction
        # fails because the user does not have enough balance
        del tx.options.gas_price
        del tx.options.max_fee_per_gas
        del tx.options.max_priority_fee_per_gas

        full_cost.l1_gas_limit = self.estimate_gas_deposit(tx)

        return full_cost

    def get_priority_op_confirmation(self, tx_hash: HexStr, index: int = 0):
        """
        Returns the transaction confirmation data that is part of `L2->L1` message.

        :param tx_hash: The hash of the L2 transaction where the message was initiated.
        :param index: In case there were multiple transactions in one message, you may pass an index of the
                      transaction which confirmation data should be fetched.
        """
        return self._zksync_web3.zksync.get_priority_op_confirmation(tx_hash, index)

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
        if transaction.token.lower() == LEGACY_ETH_ADDRESS:
            transaction.token = ETH_ADDRESS_IN_CONTRACTS

        bridge_hub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        base_token_address = bridge_hub.functions.baseToken(chain_id).call()
        is_eth_base_chain = base_token_address == ETH_ADDRESS_IN_CONTRACTS

        if is_eth_base_chain and is_address_eq(
            transaction.token, ETH_ADDRESS_IN_CONTRACTS
        ):
            return self._deposit_eth_to_eth_based_chain(transaction)
        elif is_eth_base_chain:
            return self._deposit_token_to_eth_based_chain(transaction)
        elif is_address_eq(transaction.token, ETH_ADDRESS_IN_CONTRACTS):
            tx = self._deposit_eth_to_non_eth_based_chain(transaction)
            return tx
        elif is_address_eq(transaction.token, base_token_address):
            tx = self._deposit_base_token_to_non_eth_based_chain(transaction)
            return tx
        else:
            tx = self._deposit_non_base_token_to_non_eth_based_chain(transaction)
            return tx

    def estimate_gas_deposit(self, transaction: DepositTransaction) -> int:
        """
        Estimates the amount of gas required for a deposit transaction on L1 network.
        Gas of approving ERC20 token is not included in estimation.

        :param transaction: DepositTransaction class. Not optional arguments are token(L1 token address) and amount.
        """
        if is_address_eq(transaction.token, LEGACY_ETH_ADDRESS):
            transaction.token = ETH_ADDRESS_IN_CONTRACTS

        tx = self.prepare_deposit_tx(transaction)

        base_gas_limit: int
        if is_address_eq(transaction.token, self.get_base_token()):
            base_gas_limit = self.estimate_gas_request_execute(tx)
        else:
            base_gas_limit = self._eth_web3.eth.estimate_gas(tx)

        return scale_gas_limit(base_gas_limit)

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
        if self._zksync_web3.zksync.is_base_token(token):
            func_call = TxFunctionCall(
                to=to, from_=from_, value=amount, gas_per_pub_data=gas_per_pubdata_byte
            )
            return self._zksync_web3.zksync.zks_estimate_l1_to_l2_execute(func_call.tx)
        else:
            bridge_addresses = self._zksync_web3.zksync.zks_get_bridge_contracts()

        value = 0
        l1_bridge_address = bridge_addresses.shared_l1_default_bridge
        l2_bridge_address = bridge_addresses.shared_l2_default_bridge
        token_contract = self._eth_web3.eth.contract(
            Web3.to_checksum_address(token), abi=get_erc20_abi()
        )
        bridge_data = get_custom_bridge_data(token_contract)

        return self.estimate_custom_bridge_deposit_l2_gas(
            l1_bridge_address,
            l2_bridge_address,
            (
                ETH_ADDRESS_IN_CONTRACTS
                if is_address_eq(token, LEGACY_ETH_ADDRESS)
                else token
            ),
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

        shared_bridge_address = (
            self._zksync_web3.zksync.zks_get_bridge_contracts().shared_l1_default_bridge
        )
        shared_bridge = self._eth_web3.eth.contract(
            address=shared_bridge_address, abi=l1_shared_bridge_abi_default()
        )
        tx = shared_bridge.functions.finalizeWithdrawal(
            self._zksync_web3.eth.chain_id,
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

        l1_bridge: Contract
        if self._zksync_web3.zksync.is_base_token(sender):
            l1_bridge = self.get_l1_bridge_contracts().shared
        else:
            l2_bridge = self._zksync_web3.eth.contract(
                Web3.to_checksum_address(sender), abi=l2_shared_bridge_abi_default()
            )
            l1_bridge = self._eth_web3.eth.contract(
                Web3.to_checksum_address(l2_bridge.functions.l1Bridge().call()),
                abi=l1_shared_bridge_abi_default(),
            )

        return l1_bridge.functions.isWithdrawalFinalized(
            self._zksync_web3.eth.chain_id, int(log["l1BatchNumber"], 16), proof.id
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
        signed_tx = self._l1_account.sign_transaction(transaction)
        tx_hash = self._eth_web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return tx_hash

    def check_if_l1_chain_is_london_ready(self):
        head = self._eth_web3.eth.get_block("latest")
        if head["baseFeePerGas"] is not None:
            return True, head
        return False, head

    def get_request_execute_transaction(self, transaction: RequestExecuteCallMsg):
        """
        Returns populated deposit transaction.

        :param transaction: RequestExecuteCallMsg class, required parameters are:
            contract_address(L2 contract to be called) and call_data (the input of the L2 transaction).
        """
        bridgehub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        is_eth_based_chain = self.is_eth_based_chain()

        if transaction.options is None:
            transaction.options = TransactionOptions()
        if transaction.factory_deps is None:
            transaction.factory_deps = []
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
            is_ready, head = self.check_if_l1_chain_is_london_ready()
            if is_ready:
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

        l2_costs = base_cost + transaction.operator_tip + transaction.l2_value
        provided_value = (
            transaction.options.value if is_eth_based_chain else transaction.mint_value
        )

        if provided_value == 0 or provided_value is None:
            provided_value = l2_costs
            if is_eth_based_chain:
                transaction.options.value = provided_value

        transaction.mint_value = provided_value

        check_base_cost(base_cost, provided_value)

        transaction_data = {
            "chainId": chain_id,
            "mintValue": provided_value,
            "l2Contract": Web3.to_checksum_address(transaction.contract_address),
            "l2Value": transaction.l2_value,
            "l2Calldata": to_bytes(transaction.call_data),
            "l2GasLimit": transaction.l2_gas_limit,
            "l2GasPerPubdataByteLimit": transaction.gas_per_pubdata_byte,
            "factoryDeps": transaction.factory_deps,
            "refundRecipient": transaction.refund_recipient,
        }

        return bridgehub.functions.requestL2TransactionDirect(
            transaction_data
        ).build_transaction(
            prepare_transaction_options(transaction.options, self.address)
        )

    def estimate_gas_request_execute(self, transaction: RequestExecuteCallMsg) -> int:
        """
        Estimates the amount of gas required for a request execute transaction.

        :param transaction: RequestExecuteCallMsg class, required parameters are:
            contract_address(L2 contract to be called) and call_data (the input of the L2 transaction).
        """
        transaction = self.get_request_execute_transaction(transaction)

        return self._eth_web3.eth.estimate_gas(transaction)

    def get_request_execute_allowance_params(self, transaction: RequestExecuteCallMsg):
        bridge_hub = self.get_bridgehub_contract()
        chain_id = self._zksync_web3.zksync.chain_id
        base_token_address = bridge_hub.functions.baseToken(chain_id).call()
        is_eth_base_chain = base_token_address == ETH_ADDRESS_IN_CONTRACTS

        if is_eth_base_chain:
            raise RuntimeError(
                "ETH token can't be approved! The address of the token does not exist on L1."
            )

        if transaction.from_ is None:
            transaction.from_ = self.address
        if transaction.refund_recipient is None:
            transaction.refund_recipient = self.address
        if transaction.l2_gas_limit == 0:
            func_call = TxFunctionCall(
                to=transaction.contract_address,
                from_=transaction.from_,
                gas_per_pub_data=transaction.gas_per_pubdata_byte,
                data=transaction.call_data,
            )
            transaction.l2_gas_limit = (
                self._zksync_web3.zksync.zks_estimate_l1_to_l2_execute(func_call.tx)
            )

        transaction.options = self.insert_gas_price_in_transaction_options(
            transaction.options
        )
        gas_price_for_estimation = (
            transaction.options.max_fee_per_gas
            if transaction.options.max_fee_per_gas is not None
            else transaction.options.gas_price
        )

        base_cost = self.get_base_cost(
            transaction.l2_gas_limit,
            transaction.gas_per_pubdata_byte,
            gas_price_for_estimation,
        )

        return (
            self.get_base_token(),
            base_cost + transaction.operator_tip + transaction.l2_value,
        )

    def insert_gas_price_in_transaction_options(
        self, options: TransactionOptions
    ) -> TransactionOptions:
        if options.gas_price is None and options.max_fee_per_gas is None:
            is_ready, head = self.check_if_l1_chain_is_london_ready()
            if is_ready:
                if options.max_priority_fee_per_gas is None:
                    options.max_priority_fee_per_gas = (
                        self._eth_web3.eth.max_priority_fee
                    )
                options.max_fee_per_gas = int(
                    ((head["baseFeePerGas"] * 3) / 2) + options.max_priority_fee_per_gas
                )
        else:
            options.gas_price = self._eth_web3.eth.gas_price

        return options
