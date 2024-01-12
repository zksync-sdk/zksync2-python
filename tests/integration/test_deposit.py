from unittest import main, TestCase, skip

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

from .test_config import LOCAL_ENV
from zksync2.core.types import Token, EthBlockParams
from zksync2.manage_contracts.zksync_contract import ZkSyncContract, _zksync_abi_default
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.provider.eth_provider import EthereumProvider


class DepositTests(TestCase):
    def setUp(self) -> None:
        self.env = LOCAL_ENV
        self.zksync = ZkSyncBuilder.build(self.env.zksync_server)
        self.eth_web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        self.account: LocalAccount = Account.from_key("7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110")
        self.eth_provider = EthereumProvider(self.zksync, self.eth_web3, self.account)
        self.zksync_contract = self.eth_web3.eth.contract(address=Web3.to_checksum_address(self.zksync.zksync.main_contract_address), abi=_zksync_abi_default())

    def test_deposit(self):
        amount = Web3.to_wei(1, "ether")
        eth_token = Token.create_eth()
        l1_balance_before = self.eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
        l2_balance_before = self.zksync.zksync.get_balance(self.account.address, EthBlockParams.LATEST.value)

        l1_tx_receipt = self.eth_provider.deposit(token=Token.create_eth(),
                                                  amount=amount,
                                                  gas_price=self.eth_web3.eth.gas_price)

        l2_hash = self.zksync.zksync.get_l2_hash_from_priority_op(l1_tx_receipt, self.zksync_contract)
        l2_tx_receipt = self.zksync.zksync.wait_for_transaction_receipt(l2_hash)
        l1_balance_after = self.eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
        l2_balance_after = self.zksync.zksync.get_balance(self.account.address, EthBlockParams.LATEST.value)

        self.assertEqual(1, l1_tx_receipt["status"], "L1 transaction should be successful")
        self.assertGreaterEqual(l2_balance_after, l2_balance_before + amount, "Balance on L2 should be increased")

    @skip("Integration test, used for develop purposes only")
    def test_deposit_usdc(self):
        usdc_token = Token(
            Web3.to_checksum_address("0xd35cceead182dcee0f148ebac9447da2c4d449c4"),
            Web3.to_checksum_address("0x852a4599217e76aa725f0ada8bf832a1f57a8a91"),
            "USDC",
            6)

        amount_usdc = 100000
        eth_provider = EthereumProvider(zksync_web3=self.zksync,
                                        eth_web3=self.eth_web3,
                                        l1_account=self.account)
        is_approved = eth_provider.approve_erc20(usdc_token, amount_usdc)
        self.assertTrue(is_approved)
        tx_receipt = eth_provider.deposit(usdc_token,
                                          amount_usdc,
                                          self.account.address)
        self.assertEqual(1, tx_receipt["status"])


if __name__ == '__main__':
    main()
