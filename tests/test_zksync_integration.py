from unittest import TestCase

from protocol.erc20_contract import ERC20Contract
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
from transaction.transaction712 import Transaction712
from zk_types.zk_types import Token, Fee, TokenAddress
from hexbytes import HexBytes


class ZkSyncIntegrationTests(TestCase):
    GAS_MIM_COST = 21000
    TEST_GAS_PRICE = 0

    # ZkSync http://206.189.96.247:3050
    # Ethereum http://206.189.96.247:8545
    ETH_TEST_URL = "http://206.189.96.247:8545"
    ZKSYNC_TEST_URL = "http://206.189.96.247:3050"

    ETH_TOKEN = Token.create_eth()

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

    def test_get_balance_of_token(self):
        ret = self.web3.zksync.eth_get_balance(self.account.address, "latest", self.ETH_TOKEN.address)
        print(f"credentials: {self.account.address}, balance : {ret}")

    def test_get_transaction_receipt(self):
        tx_hash = "0xb10c52ae1348bc3fc3a764c26bff9d928a544dabed3a8004e849bcab59a402f4"
        tx_receipt = self.web3.zksync.get_transaction_receipt(tx_hash)
        print(f"{tx_receipt}")

    def test_transfer_to_self(self):
        # TODO: check for committed value
        nonce = self.web3.zksync.get_transaction_count(self.account.address, "committed")

        web3 = Web3(Web3.HTTPProvider(self.ETH_TEST_URL))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        main_contract = self.web3.zksync.zks_main_contract()
        zksync_contract = ZkSyncContract(main_contract, web3, self.account)
        erc20_contract = ERC20Contract(web3,
                                       self.account.address,
                                       zksync_contract.contract_address,
                                       zksync_contract.account)
        encoded_function = erc20_contract.contract.encodeABI(fn_name="transfer",
                                                             args=["0xe1fab3efd74a77c23b426c302d96372140ff7d0c", 1])

        if encoded_function.startswith("0x"):
            encoded_function = encoded_function[2:]

        fee = Fee.default_fee(TokenAddress(self.ETH_TOKEN.address))

        execute = Execute(contract_address=self.ETH_TOKEN.address,
                          call_data=bytes.fromhex(encoded_function),
                          initiator_address=self.account.address,
                          fee=fee,
                          nonce=nonce)
        estimated_fee = self.estimate_fee(execute)
        execute.set_fee(estimated_fee)

        signature = self.signer.sign_typed_data(execute.transaction_request())
        tx712 = Transaction712(execute, self.chain_id)
        message = tx712.as_rlp_values(signature=signature)
        response = self.web3.zksync.send_raw_transaction(message)
        print(f"response: {response}")
        result = self.web3.zksync.wait_for_transaction_receipt(response)
        self.assertTrue(result["status"], 1)

    def estimate_fee(self, transaction: TransactionBase):
        return self.web3.zksync.zks_estimate_fee(transaction.to_transaction())
