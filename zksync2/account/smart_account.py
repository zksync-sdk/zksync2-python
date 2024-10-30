from ctypes import Union
from typing import Any

from eth_account import Account
from eth_typing import HexStr
from web3 import Web3

from zksync2.account.smart_account_utils import (
    populate_transaction_multiple_ecdsa,
    sign_payload_with_multiple_ecdsa,
    populate_transaction_ecdsa,
    sign_payload_with_ecdsa,
)
from zksync2.core.types import TransferTransaction, WithdrawTransaction, ZkBlockParams
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.utils import nonce_holder_abi_default
from zksync2.module.response_types import ZksAccountBalances
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction712 import Transaction712
from zksync2.transaction.transaction_builders import TxBase


class SmartAccount:

    def __init__(
        self,
        address: HexStr,
        secret,
        provider: Web3,
        transaction_builder=None,
        payload_signer=None,
    ):
        self._address = address
        self._secret = secret
        self.provider = provider
        self.transaction_builder = transaction_builder
        self.payload_signer = payload_signer

    @property
    def get_address(self) -> HexStr:
        """Read-only property for address"""
        return self._address

    @property
    def secret(self):
        """Read-only property for secret"""
        return self._secret

    def get_balance(
        self, block_tag=ZkBlockParams.COMMITTED.value, token_address: HexStr = None
    ) -> int:
        """
        Returns the balance of the account.

        :param block_tag: The block tag to get the balance at. Defaults to 'committed'.
        :param token_address: The token address to query balance for. Defaults to the native token.
        """
        return self.provider.zksync.zks_get_balance(
            self.get_address, block_tag, token_address
        )

    def get_all_balances(self) -> ZksAccountBalances:
        """
        Returns the balance of the account.
        """
        return self.provider.zksync.zks_get_all_account_balances(self.get_address)

    def get_deployment_nonce(self) -> int:
        nonce_holder = self.provider.eth.contract(
            Web3.to_checksum_address(ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value),
            abi=nonce_holder_abi_default(),
        )

        return nonce_holder.functions.getDeploymentNonce(self.get_address).call()

    def populate_transaction(self, tx: TxBase):
        return self.transaction_builder(
            tx, tx.tx["from"] or self._address, self._secret, self.provider
        )

    def sign_transaction(self, tx: TxBase) -> bytes:
        populated = self.populate_transaction(tx)
        populated.meta.custom_signature = self.payload_signer(
            populated.to_eip712_struct().signable_bytes(
                PrivateKeyEthSigner.get_default_domain(self.provider.eth.chain_id)
            ),
            self._secret,
            self.provider,
        )
        return populated.encode()

    def send_transaction(self, tx: TxBase):
        return self.provider.zksync.send_raw_transaction(self.sign_transaction(tx))

    def transfer(self, tx: TransferTransaction):
        transaction = self.provider.zksync.get_transfer_transaction(
            tx, self.get_address
        )

        return self.send_transaction(transaction)

    def withdraw(self, tx: WithdrawTransaction):
        """
        Initiates the withdrawal process which withdraws ETH or any ERC20 token
        from the associated account on L2 network to the target account on L1 network.

        :param tx: WithdrawTransaction class. Required parameters are token(HexStr) and amount(int).

        Returns:
        - Withdrawal hash.
        """
        from_: HexStr = self.get_address
        is_contract_address = (
            len(self.provider.eth.get_code(Web3.to_checksum_address(self.get_address)))
            != 0
        )
        if is_contract_address:
            from_ = Account.from_key(self.secret[0]).address
        transaction = self.provider.zksync.get_withdraw_transaction(tx, from_=from_)

        if is_contract_address:
            transaction.tx["from"] = self.get_address
            transaction.tx["nonce"] = tx.options.nonce or 0

        return self.send_transaction(transaction)


class MultisigECDSASmartAccount:
    @classmethod
    def create(
        cls, address: HexStr, secret: [HexStr], provider: Web3
    ) -> "SmartAccount":
        return SmartAccount(
            address,
            secret,
            provider,
            populate_transaction_multiple_ecdsa,
            sign_payload_with_multiple_ecdsa,
        )


class ECDSASmartAccount:
    @classmethod
    def create(
        cls, address: HexStr, secret: [HexStr], provider: Web3
    ) -> "SmartAccount":
        return SmartAccount(
            address,
            secret,
            provider,
            populate_transaction_ecdsa,
            sign_payload_with_ecdsa,
        )
