from unittest import TestCase

from eth_account import Account
from eth_typing import HexStr
from web3 import Web3

from tests.integration.test_config import (
    EnvURL,
    address_1,
    address_2,
    DAI_L1,
    private_key_1,
    multisig_address,
    private_key_2,
)
from zksync2.account.smart_account import SmartAccount, MultisigECDSASmartAccount
from zksync2.account.wallet import Wallet
from zksync2.core.types import (
    TransferTransaction,
    ADDRESS_DEFAULT,
    ZkBlockParams,
    WithdrawTransaction,
    ETH_ADDRESS_IN_CONTRACTS,
)
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.transaction.transaction_builders import TxTransfer


class TestSmartAccount(TestCase):

    def setUp(self) -> None:
        self.env = EnvURL()
        self.zksync = ZkSyncBuilder.build(self.env.env.zksync_server)
        self.eth_web3 = Web3(Web3.HTTPProvider(self.env.env.eth_server))
        self.wallet = Wallet(
            self.zksync, self.eth_web3, Account.from_key(private_key_1)
        )
        self.base_account = Account.from_key(private_key_1)
        self.account: SmartAccount = MultisigECDSASmartAccount.create(
            multisig_address, [private_key_1, private_key_2], self.zksync
        )

    def test_get_address(self):
        result = self.account.get_address
        self.assertEqual(multisig_address, result)

    def test_get_balance(self):
        result = self.account.get_balance()
        self.assertGreater(result, 0)

    def test_get_all_balances(self):
        result = self.account.get_all_balances()
        expected = 2 if self.wallet.is_eth_based_chain() else 3
        self.assertEqual(len(result), expected)

    def test_get_deployment_nonce(self):
        result = self.account.get_deployment_nonce()
        self.assertIsNotNone(result)

    def test_populate_transaction(self):
        result = self.account.populate_transaction(
            TxTransfer(
                from_=multisig_address,
                to=address_2,
                value=7_000_000_000,
                token=ADDRESS_DEFAULT,
            )
        )
        self.assertIsNotNone(result)

    def test_transfer_eth(self):
        if self.wallet.is_eth_based_chain():
            amount = 7_000_000
            balance_before_transfer = self.zksync.zksync.zks_get_balance(
                Web3.to_checksum_address(address_2), token_address=ADDRESS_DEFAULT
            )
            tx_hash = self.account.transfer(
                TransferTransaction(
                    to=Web3.to_checksum_address(address_2),
                    token_address=ADDRESS_DEFAULT,
                    amount=amount,
                )
            )

            self.zksync.zksync.wait_for_transaction_receipt(
                tx_hash, timeout=240, poll_latency=0.5
            )
            balance_after_transfer = self.zksync.zksync.zks_get_balance(
                Web3.to_checksum_address(address_2), token_address=ADDRESS_DEFAULT
            )

            self.assertEqual(balance_after_transfer - balance_before_transfer, amount)
        else:
            amount = 7_000_000_000
            l2_token = self.wallet.l2_token_address(ETH_ADDRESS_IN_CONTRACTS)
            balance_before_transfer = self.zksync.zksync.zks_get_balance(
                Web3.to_checksum_address(address_2), token_address=l2_token
            )
            tx_hash = self.account.transfer(
                TransferTransaction(
                    to=Web3.to_checksum_address(address_2),
                    token_address=ADDRESS_DEFAULT,
                    amount=amount,
                )
            )

            self.zksync.zksync.wait_for_transaction_receipt(
                tx_hash, timeout=240, poll_latency=0.5
            )
            balance_after_transfer = self.zksync.zksync.zks_get_balance(
                Web3.to_checksum_address(address_2), token_address=l2_token
            )

            self.assertEqual(balance_after_transfer - balance_before_transfer, amount)

    def test_transfer_token(self):
        amount = 5
        l2_address = self.wallet.l2_token_address(DAI_L1)

        sender_before = self.account.get_balance(token_address=l2_address)
        balance_before = self.zksync.zksync.zks_get_balance(
            address_2,
            token_address=l2_address,
            block_tag=ZkBlockParams.LATEST.value,
        )
        tx_hash = self.account.transfer(
            TransferTransaction(
                to=Web3.to_checksum_address(address_2),
                token_address=Web3.to_checksum_address(l2_address),
                amount=amount,
            )
        )

        result = self.zksync.zksync.wait_finalized(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertIsNotNone(result)
        sender_after = self.account.get_balance(token_address=l2_address)

        balance_after = self.zksync.zksync.zks_get_balance(
            address_2,
            token_address=l2_address,
            block_tag=ZkBlockParams.LATEST.value,
        )

        self.assertEqual(amount, sender_before - sender_after)
        self.assertEqual(amount, balance_after - balance_before)

    def test_withdraw_eth(self):
        if self.wallet.is_eth_based_chain():
            l2_balance_before = self.wallet.get_balance(token_address=ADDRESS_DEFAULT)
            amount = 7_000_000

            withdraw_tx_hash = self.account.withdraw(
                WithdrawTransaction(token=ADDRESS_DEFAULT, amount=amount, to=address_2)
            )

            withdraw_receipt = self.zksync.zksync.wait_finalized(
                withdraw_tx_hash, timeout=240, poll_latency=0.5
            )
            self.assertFalse(
                self.wallet.is_withdrawal_finalized(withdraw_receipt["transactionHash"])
            )
            finalized_hash = self.wallet.finalize_withdrawal(
                withdraw_receipt["transactionHash"]
            )
            result = self.eth_web3.eth.wait_for_transaction_receipt(
                finalized_hash, timeout=240, poll_latency=0.5
            )

            l2_balance_after = self.account.get_balance(token_address=ADDRESS_DEFAULT)

            self.assertIsNotNone(result)
            self.assertGreater(
                l2_balance_before,
                l2_balance_after,
                "L2 balance should be lower after withdrawal",
            )
        else:
            l2_token = self.wallet.l2_token_address(ETH_ADDRESS_IN_CONTRACTS)
            l2_balance_before = self.wallet.get_balance(token_address=l2_token)
            amount = 7_000_000_000

            withdraw_tx_hash = self.wallet.withdraw(
                WithdrawTransaction(token=ADDRESS_DEFAULT, amount=amount)
            )

            withdraw_receipt = self.zksync.zksync.wait_finalized(
                withdraw_tx_hash, timeout=240, poll_latency=0.5
            )
            self.assertFalse(
                self.wallet.is_withdrawal_finalized(withdraw_receipt["transactionHash"])
            )
            finalized_hash = self.wallet.finalize_withdrawal(
                withdraw_receipt["transactionHash"]
            )
            result = self.eth_web3.eth.wait_for_transaction_receipt(
                finalized_hash, timeout=240, poll_latency=0.5
            )

            l2_balance_after = self.account.get_balance(token_address=l2_token)

            self.assertIsNotNone(result)
            self.assertGreater(
                l2_balance_before,
                l2_balance_after,
                "L2 balance should be lower after withdrawal",
            )

    def test_withdraw_token(self):
        l2_address = self.wallet.l2_token_address(DAI_L1)
        l2_balance_before = self.account.get_balance(
            token_address=Web3.to_checksum_address(l2_address)
        )

        withdraw_tx_hash = self.account.withdraw(
            WithdrawTransaction(Web3.to_checksum_address(l2_address), 5)
        )
        withdraw_receipt = self.zksync.zksync.wait_finalized(
            withdraw_tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertFalse(
            self.wallet.is_withdrawal_finalized(withdraw_receipt["transactionHash"])
        )

        finalized_hash = self.wallet.finalize_withdrawal(
            withdraw_receipt["transactionHash"]
        )
        result = self.eth_web3.eth.wait_for_transaction_receipt(
            finalized_hash, timeout=240, poll_latency=0.5
        )

        l2_balance_after = self.account.get_balance(
            token_address=Web3.to_checksum_address(l2_address)
        )

        self.assertIsNotNone(result)
        self.assertGreater(
            l2_balance_before,
            l2_balance_after,
            "L2 balance should be lower after withdrawal",
        )
