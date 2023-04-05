import os
from unittest import TestCase, skip
from web3 import Web3
from tests.test_config import TESTNET, EnvPrivateKey
from zksync2.core.types import Token, EthBlockParams
from zksync2.module.module_builder import ZkSyncBuilder
from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.provider.eth_provider import EthereumProvider


def generate_random_salt() -> bytes:
    return os.urandom(32)


class ZkSyncWeb3Tests(TestCase):

    def setUp(self) -> None:
        self.env = TESTNET
        env_key = EnvPrivateKey("ZKSYNC_KEY1")
        self.zksync = ZkSyncBuilder.build(self.env.zksync_server)
        self.eth_web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        self.account: LocalAccount = Account.from_key(env_key.key)
        self.eth_provider = EthereumProvider(self.zksync, self.eth_web3, self.account)

    def test_deposit(self):
        amount = Web3.to_wei(1, "ether")
        eth_token = Token.create_eth()
        gas_price = self.eth_web3.eth.gas_price
        before_deposit = self.eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
        print(f"Before: {before_deposit}")
        l1_tx_receipt = self.eth_provider.deposit(token=Token.create_eth(),
                                                  amount=amount,
                                                  gas_price=gas_price)
        # TODO: when L2 tx

        after = self.eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
        print(f"After : {after}")

        self.assertEqual(1, l1_tx_receipt["status"])

    @skip("Integration test, used for develop purposes only")
    def test_deposit_usdc(self):
        USDC_TOKEN = Token(
            Web3.to_checksum_address("0xd35cceead182dcee0f148ebac9447da2c4d449c4"),
            Web3.to_checksum_address("0x852a4599217e76aa725f0ada8bf832a1f57a8a91"),
            "USDC",
            6)

        amount_usdc = 100000
        eth_provider = EthereumProvider(zksync_web3=self.zksync,
                                        eth_web3=self.eth_web3,
                                        l1_account=self.account)
        is_approved = eth_provider.approve_erc20(USDC_TOKEN, amount_usdc)
        self.assertTrue(is_approved)
        tx_receipt = eth_provider.deposit(USDC_TOKEN,
                                          amount_usdc,
                                          self.account.address)
        self.assertEqual(1, tx_receipt["status"])