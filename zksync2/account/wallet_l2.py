from eth_account.signers.base import BaseAccount
from web3 import Web3

from eth_typing import HexStr
from web3 import Web3

from zksync2.account.utils import prepare_transaction_options, options_from_712
from zksync2.core.types import (
    ZkBlockParams,
    L2BridgeContracts,
    TransferTransaction,
    TransactionOptions,
    WithdrawTransaction,
    ADDRESS_DEFAULT,
)
from zksync2.core.utils import is_eth
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.utils import (
    zksync_abi_default,
    nonce_holder_abi_default,
    l2_bridge_abi_default,
    get_erc20_abi,
)
from zksync2.module.request_types import EIP712Meta
from zksync2.module.response_types import ZksAccountBalances
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction712 import Transaction712
from zksync2.transaction.transaction_builders import TxFunctionCall, TxWithdraw


class WalletL2:
    def __init__(self, zksync_web3: Web3, eth_web3: Web3, l1_account: BaseAccount):
        self._eth_web3 = eth_web3
        self._zksync_web3 = zksync_web3
        self._main_contract_address = self._zksync_web3.zksync.zks_main_contract()
        self._l1_account = l1_account
        self.contract = self._eth_web3.eth.contract(
            Web3.to_checksum_address(self._main_contract_address),
            abi=zksync_abi_default(),
        )

    def get_balance(
        self, block_tag=ZkBlockParams.COMMITTED.value, token_address: HexStr = None
    ) -> int:
        """
            Returns the balance of the account.

            :param block_tag: The block tag to get the balance at. Defaults to 'committed'.
            :param token_address: The token address to query balance for. Defaults to the native token.
        """
        return self._zksync_web3.zksync.zks_get_balance(
            self._l1_account.address, block_tag, token_address
        )

    def get_all_balances(self) -> ZksAccountBalances:
        """
        Returns the balance of the account.
        """
        return self._zksync_web3.zksync.zks_get_all_account_balances(
            self._l1_account.address
        )

    def get_deployment_nonce(self) -> int:
        """
        Returns all token balances of the account.
        """
        nonce_holder = self._zksync_web3.zksync.contract(
            address=ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value,
            abi=nonce_holder_abi_default(),
        )
        deployment_nonce = nonce_holder.functions.getDeploymentNonce(
            self._l1_account.address
        ).call({"from": self._l1_account.address})
        return deployment_nonce

    def get_l2_bridge_contracts(self) -> L2BridgeContracts:
        """
        Returns L2 bridge contracts.
        """
        addresses = self._zksync_web3.zksync.zks_get_bridge_contracts()
        return L2BridgeContracts(
            erc20=self._zksync_web3.eth.contract(
                address=Web3.to_checksum_address(addresses.erc20_l2_default_bridge),
                abi=l2_bridge_abi_default(),
            ),
            weth=self._zksync_web3.eth.contract(
                address=Web3.to_checksum_address(addresses.weth_bridge_l2),
                abi=l2_bridge_abi_default(),
            ),
        )

    def transfer(self, tx: TransferTransaction) -> HexStr:
        """
        Transfer ETH or any ERC20 token within the same interface.

        :param tx: TransferTransaction class. Required parameters are to and amount.

        Returns:
        - Transaction hash.
        """
        tx_fun_call = self._zksync_web3.zksync.get_transfer_transaction(
            tx, self._l1_account.address
        )
        if tx.options.gas_limit == 0:
            tx_712 = tx_fun_call.tx712(
                self._zksync_web3.zksync.zks_estimate_gas_transfer(tx_fun_call.tx)
            )
        signer = PrivateKeyEthSigner(self._l1_account, tx.options.chain_id)
        signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())

        msg = tx_712.encode(signed_message)
        tx_hash = self._zksync_web3.zksync.send_raw_transaction(msg)

        return tx_hash

    def withdraw(self, tx: WithdrawTransaction):
        """
        Initiates the withdrawal process which withdraws ETH or any ERC20 token
        from the associated account on L2 network to the target account on L1 network.

        :param tx: WithdrawTransaction class. Required parameters are token(HexStr) and amount(int).

        Returns:
        - Withdrawal hash.
        """
        if tx.options is None:
            tx.options = TransactionOptions()
        if tx.options.chain_id is None:
            tx.options.chain_id = self._zksync_web3.zksync.chain_id
        if tx.options.nonce is None:
            tx.options.nonce = self._zksync_web3.zksync.get_transaction_count(
                Web3.to_checksum_address(self._l1_account.address),
                ZkBlockParams.LATEST.value,
            )
        if tx.options.gas_price is None:
            tx.options.gas_price = self._zksync_web3.zksync.gas_price

        if not is_eth(tx.token):
            if tx.bridge_address is None:
                l2_weth_token = ADDRESS_DEFAULT
                try:
                    l2_weth_token = (
                        self.get_l2_bridge_contracts()
                        .weth.functions.l1TokenAddress(tx.token)
                        .call()
                    )
                except:
                    pass
                if l2_weth_token == ADDRESS_DEFAULT:
                    tx.bridge_address = Web3.to_checksum_address(self.get_l2_bridge_contracts().erc20.address)
                else:
                    tx.bridge_address = Web3.to_checksum_address(self.get_l2_bridge_contracts().weth.address)

        transaction = TxWithdraw(
            web3=self._zksync_web3,
            account=self._l1_account,
            chain_id=tx.options.chain_id,
            nonce=tx.options.nonce,
            to=tx.to,
            amount=tx.amount,
            gas_limit=0 if tx.options.gas_limit is None else tx.options.gas_limit,
            gas_price=tx.options.gas_price,
            token=tx.token,
            bridge_address=tx.bridge_address,
            paymaster_params=tx.paymaster_params
        )
        signer = PrivateKeyEthSigner(self._l1_account, tx.options.chain_id)
        estimated_gas = self._zksync_web3.zksync.eth_estimate_gas(transaction.tx)
        tx_712 = transaction.tx712(estimated_gas)
        signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())

        msg = tx_712.encode(signed_message)

        return self._zksync_web3.zksync.send_raw_transaction(msg)