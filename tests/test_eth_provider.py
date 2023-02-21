import os
from unittest import TestCase
from web3 import Web3
from web3.types import TxParams

from tests.test_config import ZKSYNC_TEST_URL, ETH_TEST_URL, PRIVATE_KEY2
from zksync2.core.types import Token, EthBlockParams
from zksync2.manage_contracts.zksync_contract import ZkSyncContract

from zksync2.manage_contracts.gas_provider import StaticGasProvider
from zksync2.module.module_builder import ZkSyncBuilder
from eth_account import Account
from eth_account.signers.local import LocalAccount

from zksync2.provider.eth_provider import EthereumProvider
from zksync2.signer.eth_signer import PrivateKeyEthSigner


def generate_random_salt() -> bytes:
    return os.urandom(32)


class ZkSyncWeb3Tests(TestCase):

    def setUp(self) -> None:
        self.zksync = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
        self.eth_web3 = Web3(Web3.HTTPProvider(ETH_TEST_URL))
        self.account: LocalAccount = Account.from_key(PRIVATE_KEY2)
        # self.chain_id = self.zksync.zksync.chain_id
        # self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        # TODO: use Eth Web3
        self.zksync_contract = ZkSyncContract(self.zksync.zksync.zks_main_contract(),
                                              self.eth_web3,
                                              self.account)
        self.eth_provider = EthereumProvider(self.zksync, self.eth_web3, self.account)

    def test_deposit(self):
        amount = Web3.toWei(0.01, "ether")
        eth_token = Token.create_eth()
        gas_price = self.eth_web3.eth.gas_price
        before_deposit = self.eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
        print(f"Before: {before_deposit}")
        op = self.eth_provider.deposit(token=Token.create_eth(),
                                       amount=amount,
                                       gas_price=gas_price)
        print(f"Op: {op}")
        after = self.eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
        print(f"After : {after}")
