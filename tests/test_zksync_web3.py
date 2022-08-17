from unittest import TestCase

from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.types import TxParams, BlockParams
from web3.middleware import geth_poa_middleware

from protocol.utility_contracts.gas_provider import StaticGasProvider
from protocol.zksync_contract import ZkSyncContract
from protocol.zksync_web3.zksync_web3_builder import ZkSyncBuilder
from protocol.core.types import Token
from eth_account import Account
from eth_account.signers.local import LocalAccount

from crypto.eth_signer import PrivateKeyEthSigner
from protocol.eth_provider import EthereumProvider


class ZkSyncWeb3Tests(TestCase):
    GAS_LIMIT = 21000
    GAS_PRICE = 0
    # GAS_MIM_COST = 21000
    # TEST_GAS_PRICE = 0

    # ZkSync http://206.189.96.247:3050
    # Ethereum http://206.189.96.247:8545
    ETH_TEST_URL = "http://206.189.96.247:8545"
    ZKSYNC_TEST_URL = "http://206.189.96.247:3050"

    ETH_TOKEN = Token.create_eth()

    DEFAULT_BLOCK_PARAM_NAME: BlockParams = "latest"
    PRIVATE_KEY = b'\00' * 31 + b'\01'

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.ZKSYNC_TEST_URL)
        # address under Java from bigint(1) private key: "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"
        self.account: LocalAccount = Account.from_key(self.PRIVATE_KEY)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.gas_provider = StaticGasProvider(Web3.toWei(1, "gwei"), 555000)
        self.CONTRACT_ADDRESS = HexStr("0x5bb4c6b82d3bcef0417c1e0152e7e1ba763e72c8")

    def test_send_money(self):
        web3 = Web3(Web3.HTTPProvider(self.ETH_TEST_URL))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        account = web3.eth.accounts[0]
        transaction: TxParams = {
            "from": account,
            "gasPrice": web3.toWei(1, "gwei"),
            "gas": self.GAS_LIMIT,
            "to": self.account.address,
            "value": web3.toWei(1000000, 'ether')
        }
        tx_hash = web3.eth.send_transaction(transaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(txn_receipt['status'], 1)

    def test_deposit(self):
        web3 = Web3(Web3.HTTPProvider(self.ETH_TEST_URL))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        eth_provider = EthereumProvider.build_ethereum_provider(zksync=self.web3,
                                                                eth=web3,
                                                                account=self.account,
                                                                gas_provider=self.gas_provider)
        tx_receipt = eth_provider.deposit(self.ETH_TOKEN, web3.toWei(100, "ether"), self.account.address)
        print(f"receipt: {tx_receipt}")

    def test_get_balance_of_token(self):
        balance = self.web3.zksync.eth_get_balance(self.account.address,
                                                   self.DEFAULT_BLOCK_PARAM_NAME,
                                                   self.ETH_TOKEN.l2_address)
        print(f"balance: {balance}")
