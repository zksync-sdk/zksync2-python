from eth_account.signers.base import BaseAccount
from eth_typing import HexStr
from web3 import Web3

from zksync2.core.types import (
    ZkBlockParams,
    L2BridgeContracts,
    TransferTransaction,
    WithdrawTransaction,
)
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.utils import (
    get_zksync_hyperchain,
    nonce_holder_abi_default,
    l2_bridge_abi_default,
    l2_shared_bridge_abi_default,
)
from zksync2.module.response_types import ZksAccountBalances
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction712 import Transaction712


class WalletL2:
    def __init__(self, zksync_web3: Web3, eth_web3: Web3, l1_account: BaseAccount):
        self._eth_web3 = eth_web3
        self._zksync_web3 = zksync_web3
        self._main_contract_address = self._zksync_web3.zksync.zks_main_contract()
        self._l1_account = l1_account
        self.contract = self._eth_web3.eth.contract(
            Web3.to_checksum_address(self._main_contract_address),
            abi=get_zksync_hyperchain(),
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
            shared=self._zksync_web3.eth.contract(
                address=Web3.to_checksum_address(addresses.shared_l2_default_bridge),
                abi=l2_shared_bridge_abi_default(),
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

        if tx.options.gas_limit is None or tx.options.gas_limit == 0:
            tx.options.gas_limit = self._zksync_web3.zksync.eth_estimate_gas(
                tx_fun_call.tx
            )

        tx_712 = tx_fun_call.tx712(tx.options.gas_limit)
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
        transaction = self._zksync_web3.zksync.get_withdraw_transaction(
            tx, from_=self._l1_account.address
        )
        if tx.options.gas_limit is None:
            transaction.tx["gas"] = self._zksync_web3.zksync.eth_estimate_gas(
                transaction.tx
            )
        else:
            transaction.tx["gas"] = tx.options.gas_limit
        tx_712 = transaction.tx712()
        signer = PrivateKeyEthSigner(self._l1_account, self._zksync_web3.eth.chain_id)
        signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())

        msg = tx_712.encode(signed_message)

        return self._zksync_web3.zksync.send_raw_transaction(msg)
