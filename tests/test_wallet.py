from unittest import TestCase
from eth_account import Account
from eth_account.signers.local import LocalAccount
from crypto.eth_signer import PrivateKeyEthSigner
from zksync_wallet import ZkSyncWallet
from zk_types.zk_types import *
from protocol.zksync import ZkSyncBuilder

# import logging
# import sys
# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class TestZkSync(TestCase):
    PRIVATE_KEYS = ['0xa045b52470d306ff78e91b0d2d92f90f7504189125a46b69423dc673fd6b4f3e',
                    '0x601b47729b2820e94bc10125edc8d534858827428b449175a275069dc00c303f',
                    '0xa7adf8459b4c9a62f09e0e5390983c0145fa20e88c9e5bf837d8bf3dcd05bd9c']

    url_testnet = "https://zksync2-testnet.zksync.dev"
    TOKEN_ADDRESS = TokenAddress(HexStr('0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'))

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.url_testnet)
        account: LocalAccount = Account.from_key(self.PRIVATE_KEYS[0])
        self.signer = PrivateKeyEthSigner(account, HexBytes(5))
        self.wallet = ZkSyncWallet(self.web3.zksync, self.signer)

    def test_wallet_get_balance(self):
        balance = self.wallet.get_balance()
        self.assertEqual(0, balance)

    def test_get_nonce(self):
        nonce = self.wallet.get_nonce()
        self.assertEqual(0, nonce)
