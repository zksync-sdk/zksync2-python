from unittest import TestCase

from protocol.zksync_contract import ZkSyncContract
from transaction.transaction import TransactionBase, Execute, DeployContract, Withdraw
from protocol.zksync import ZkSyncBuilder

# from eip712_structs import make_domain
from eth_account import Account
from eth_account.signers.local import LocalAccount

from crypto.eth_signer import PrivateKeyEthSigner
from protocol.eth_provider import EthereumProvider
from web3 import Web3
from web3.types import TxParams
from web3.middleware import geth_poa_middleware

# from eth_account.signers.local import LocalAccount
# from eth_typing import HexStr
# from hexbytes import HexBytes
# from web3 import Web3
# from transaction.transaction import Withdraw
from zk_types.zk_types import Token, Fee, TokenAddress


class ZkSyncIntegrationTests(TestCase):

    GAS_MIM_COST = 21000
    TEST_GAS_PRICE = 0

    # ZkSync http://206.189.96.247:3050
    # Ethereum http://206.189.96.247:8545
    ETH_TEST_URL = "http://206.189.96.247:8545"
    ZKSYNC_TEST_URL = "http://206.189.96.247:3050"

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.ZKSYNC_TEST_URL)
        self.account: LocalAccount = Account.create(1)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)

    def test_send_money(self):
        web3 = Web3(Web3.HTTPProvider(self.ETH_TEST_URL))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        account = web3.eth.accounts[0]
        transaction: TxParams = {
            "from": account,
            "gasPrice": self.TEST_GAS_PRICE,
            "gas": self.GAS_MIM_COST,
            "to": self.account.address,
            "value": web3.toWei(10, 'ether')
        }
        tx_hash = web3.eth.send_transaction(transaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(txn_receipt['status'], 1)

    def test_deposit(self):
        web3 = Web3(Web3.HTTPProvider(self.ETH_TEST_URL))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        main_contract = self.web3.zksync.zks_main_contract()
        zksync_contract = ZkSyncContract(main_contract, web3, self.account)
        eth_provider = EthereumProvider(web3, zksync_contract)
        ret = eth_provider.deposit(Token.create_eth(), web3.toWei(9, 'ether'), self.account.address)
        print(f"ret = {ret}")
