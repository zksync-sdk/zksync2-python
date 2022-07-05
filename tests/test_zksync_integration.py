from unittest import TestCase
from transaction.transaction import TransactionBase, Execute, DeployContract, Withdraw
from protocol.zksync import ZkSyncBuilder

# from eip712_structs import make_domain
from eth_account import Account
from eth_account.signers.local import LocalAccount

from crypto.eth_signer import PrivateKeyEthSigner
from web3 import Web3
from web3.types import TxParams
from web3.middleware import geth_poa_middleware

# from eth_account.signers.local import LocalAccount
# from eth_typing import HexStr
# from hexbytes import HexBytes
# from web3 import Web3
# from transaction.transaction import Withdraw
# from zk_types.zk_types import Token, Fee, TokenAddress


class ZkSyncIntegrationTests(TestCase):

    GAS_MIM_COST = 21000
    TEST_GAS_PRICE = 0

    # ZkSync http://206.189.96.247:3050
    # Ethereum http://206.189.96.247:8545

    def setUp(self) -> None:
        # self.web3 = ZkSyncBuilder.build("http://127.0.0.1:3050")
        self.web3 = ZkSyncBuilder.build("http://206.189.96.247:3050")
        self.account: LocalAccount = Account.create(1)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.contract_address = "0x2946259e0334f33a064106302415ad3391bed384"

    def test_send_money(self):
        # web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
        web3 = Web3(Web3.HTTPProvider("http://206.189.96.247:8545"))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        account = web3.eth.accounts[0]
        # Transaction.createEtherTransaction(account, null, BigInteger.ZERO, BigInteger.valueOf(21_000L),
        #                                    this.credentials.getAddress(),
        #                                    Convert.toWei("10", Unit.ETHER).toBigInteger()))
        # public
        # static Transaction
        # createEtherTransaction(String from, BigInteger nonce, BigInteger gasPrice, BigInteger gasLimit, String to,
        #                        BigInteger value)
        # {
        #   return new Transaction( from, nonce, gasPrice, gasLimit, to, value, null);
        # }

        block = web3.eth.get_block('latest')
        transaction: TxParams = {
            "from": account,
            "nonce": block['number'] + 1,
            "gasPrice": self.TEST_GAS_PRICE,
            "gas": self.GAS_MIM_COST,
            "to": self.account.address,
            "value": web3.toWei(10, 'ether')
        }
        tx_hash = web3.eth.send_transaction(transaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"txn receipt: {txn_receipt}")

    # def test_deposit(self):
