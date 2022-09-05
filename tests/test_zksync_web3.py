from unittest import TestCase

from eth_typing import HexStr
from web3 import Web3
from web3.types import TxParams, BlockParams, Nonce
from web3.middleware import geth_poa_middleware

from protocol.request.request_types import FunctionCallTxBuilder, Create2ContractTransactionBuilder
from protocol.utility_contracts.contract_deployer import ContractDeployer
from protocol.utility_contracts.erc20_contract import ERC20FunctionEncoder
from protocol.utility_contracts.gas_provider import StaticGasProvider
from protocol.zksync_web3.zksync_web3_builder import ZkSyncBuilder
from protocol.utility_contracts.l2_bridge import L2BridgeEncoder
from protocol.core.types import Token, ZkBlockParams, BridgeAddresses, EthBlockParams
from eth_account import Account
from eth_account.signers.local import LocalAccount

from crypto.eth_signer import PrivateKeyEthSigner
from protocol.eth_provider import EthereumProvider
from tests.counter_contract_utils import _get_counter_contract_binary, CounterContractEncoder, CounterContract
from transaction.transaction712 import Transaction712, Transaction712Encoder


class ZkSyncWeb3Tests(TestCase):
    GAS_LIMIT = 21000
    ETH_TEST_URL = "http://206.189.96.247:8545"
    ZKSYNC_TEST_URL = "http://206.189.96.247:3050"
    ETH_TOKEN = Token.create_eth()
    DEFAULT_BLOCK_PARAM_NAME: BlockParams = "latest"
    PRIVATE_KEY = b'\00' * 31 + b'\01'
    ETH_AMOUNT_BALANCE = 100

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.ZKSYNC_TEST_URL)
        # address under Java from bigint(1) private key: "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"
        self.account: LocalAccount = Account.from_key(self.PRIVATE_KEY)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.gas_provider = StaticGasProvider(Web3.toWei(1, "gwei"), 555000)
        # self.CONTRACT_ADDRESS = HexStr("0x5bb4c6b82d3bcef0417c1e0152e7e1ba763e72c8")

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
        tx_receipt = eth_provider.deposit(self.ETH_TOKEN,
                                          web3.toWei(self.ETH_AMOUNT_BALANCE, "ether"),
                                          self.account.address)
        self.assertEqual(1, tx_receipt["status"])

    def test_get_balance_of_token(self):
        balance = self.web3.zksync.eth_get_balance(self.account.address,
                                                   self.DEFAULT_BLOCK_PARAM_NAME,
                                                   self.ETH_TOKEN.l2_address)

        # ret = int(self.ETH_TOKEN.format_token(balance))
        # self.assertEqual(self.ETH_AMOUNT_BALANCE, ret)
        print(f"balance: {balance}")

    def test_nonce(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, self.DEFAULT_BLOCK_PARAM_NAME)
        print(f"Nonce: {nonce}")

    def test_transaction_receipt(self):
        tx_hash = "0xf53d38388cd8e5292683509c9a9f373e2c7d3766f41256b9cbf7d966552a46ff"
        receipt = self.web3.zksync.get_transaction_receipt(tx_hash)
        print(f"receipt: {receipt}")

    def test_estimate_gas_transfer_native(self):
        tx_builder = FunctionCallTxBuilder(from_=self.account.address,
                                           to=self.account.address,
                                           ergs_price=0,
                                           ergs_limit=0,
                                           data=HexStr("0x"))
        tx = tx_builder.build()
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx)
        print(f"test_estimate_gas_transfer_native, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_gas_transfer_native, estimate_gas must be greater 0")

    def test_transfer_native_to_self(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, self.DEFAULT_BLOCK_PARAM_NAME)
        to = HexStr(Web3.toChecksumAddress("0xc513d436b5ac85a36cc4f6956ec11b500693aabd"))

        tx_builder = FunctionCallTxBuilder(from_=self.account.address,
                                           to=to,
                                           ergs_price=0,
                                           ergs_limit=0,
                                           data=HexStr("0x"))
        tx = tx_builder.build()
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx)
        gas_price = self.web3.zksync.gas_price

        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = Transaction712(chain_id=self.chain_id,
                                nonce=nonce,
                                gas_limit=estimate_gas,
                                to=tx["to"],
                                value=Web3.toWei(1, 'ether'),
                                data=tx["data"],
                                maxPriorityFeePerGas=100000000,
                                maxFeePerGas=gas_price,
                                from_=self.account.address,
                                meta=tx["eip712Meta"])

        eip712_structured = tx_712.to_eip712_struct()
        signature = self.signer.sign_typed_data(eip712_structured)
        msg = Transaction712Encoder.encode(tx_712, signature)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(1, tx_receipt["status"])

    def test_transfer_native_to_self_web3_legacy(self):
        # TODO: add implementation
        pass

    def test_transfer_native_to_self_web3(self):
        # TODO: add implementation
        pass

    def test_transfer_token_to_self(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        tokens = self.web3.zksync.zks_get_confirmed_tokens(0, 100)
        not_eth_tokens = [x for x in tokens if not x.is_eth()]
        self.assertTrue(bool(not_eth_tokens), "Can't get non eth tokens")
        token_address = not_eth_tokens[0].l2_address

        erc20_encoder = ERC20FunctionEncoder(self.web3)
        transfer_params = [self.account.address, 0]
        call_data = erc20_encoder.encode_method("transfer", args=transfer_params)

        tx_builder = FunctionCallTxBuilder(from_=self.account.address,
                                           to=token_address,
                                           ergs_price=0,
                                           ergs_limit=0,
                                           data=call_data)
        tx = tx_builder.build()
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx)
        gas_price = self.web3.zksync.gas_price

        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = Transaction712(chain_id=self.chain_id,
                                nonce=nonce,
                                gas_limit=estimate_gas,
                                to=tx["to"],
                                value=tx["value"],
                                data=tx["data"],
                                maxPriorityFeePerGas=100000000,
                                maxFeePerGas=gas_price,
                                from_=self.account.address,
                                meta=tx["eip712Meta"])
        eip712_structured = tx_712.to_eip712_struct()
        signature = self.signer.sign_typed_data(eip712_structured)
        msg = Transaction712Encoder.encode(tx_712, signature)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(1, tx_receipt["status"])

    def test_estimate_gas_withdraw(self):
        bridges = self.web3.zksync.zks_get_bridge_contracts()
        l2_func_encoder = L2BridgeEncoder(self.web3)
        call_data = l2_func_encoder.encode_function(fn_name="withdraw", args=[
            self.account.address,
            self.ETH_TOKEN.l2_address,
            self.ETH_TOKEN.to_int(1)
        ])

        self.assertEqual("0xd9caed120000000000000000000000007e5f4552091a69125d5dfcb7b8c2659029395bdf"
                         "00000000000000000000000000000000000000000000000000000000000000000000000000"
                         "000000000000000000000000000000000000000de0b6b3a7640000", call_data)

        tx_builder = FunctionCallTxBuilder(from_=self.account.address,
                                           to=bridges.l2_eth_default_bridge,
                                           ergs_limit=0,
                                           ergs_price=0,
                                           data=HexStr(call_data))
        tx = tx_builder.build()
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx)
        print(f"test_estimate_gas_withdraw, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_gas_withdraw, estimate_gas must be greater 0")

    def test_withdraw(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        bridges: BridgeAddresses = self.web3.zksync.zks_get_bridge_contracts()

        l2_func_encoder = L2BridgeEncoder(self.web3)
        call_data = l2_func_encoder.encode_function(fn_name="withdraw", args=[
            self.account.address,
            self.ETH_TOKEN.l2_address,
            self.ETH_TOKEN.to_int(1)
        ])

        tx_builder = FunctionCallTxBuilder(from_=self.account.address,
                                           to=bridges.l2_eth_default_bridge,
                                           ergs_limit=0,
                                           ergs_price=0,
                                           data=HexStr(call_data))
        tx = tx_builder.build()
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx)
        gas_price = self.web3.zksync.gas_price

        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = Transaction712(chain_id=self.chain_id,
                                nonce=nonce,
                                gas_limit=estimate_gas,
                                to=tx["to"],
                                value=tx["value"],
                                data=tx["data"],
                                maxPriorityFeePerGas=100000000,
                                maxFeePerGas=gas_price,
                                from_=self.account.address,
                                meta=tx["eip712Meta"])
        eip712_structured = tx_712.to_eip712_struct()
        signature = self.signer.sign_typed_data(eip712_structured)
        msg = Transaction712Encoder.encode(tx_712, signature)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(1, tx_receipt["status"])

    def test_estimate_gas_execute(self):
        erc20func_encoder = ERC20FunctionEncoder(self.web3)
        transfer_args = [
            Web3.toChecksumAddress("0xe1fab3efd74a77c23b426c302d96372140ff7d0c"),
            1
        ]
        call_data = erc20func_encoder.encode_method(fn_name="transfer", args=transfer_args)
        tx_builder = FunctionCallTxBuilder(from_=self.account.address,
                                           to=Web3.toChecksumAddress("0x79f73588fa338e685e9bbd7181b410f60895d2a3"),
                                           ergs_limit=0,
                                           ergs_price=0,
                                           data=HexStr(call_data))
        tx = tx_builder.build()
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx)
        print(f"test_estimate_gas_execute, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_withdraw, estimate_gas must be greater 0")

    def test_estimate_gas_deploy_contract(self):
        counter_contract_bin = _get_counter_contract_binary()
        tx_builder = Create2ContractTransactionBuilder(web3=self.web3,
                                                      from_=self.account.address,
                                                      ergs_price=0,
                                                      ergs_limit=0,
                                                      bytecode=counter_contract_bin)
        tx = tx_builder.build()
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx)
        print(f"test_estimate_gas_deploy_contract, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_gas_deploy_contract, estimate_gas must be greater 0")

    def test_wen3py_deploy_contract(self):
        counter_contract = CounterContract.deploy(self.web3, self.account)
        print(f"Counter Contract address: {counter_contract.address}")

        v = counter_contract.get()
        self.assertEqual(v, 0)

        tx = counter_contract.increment(10)
        self.assertEqual(1, tx["status"])

        v = counter_contract.get()
        self.assertEqual(10, v)

    def test_deploy_contract_create(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        deployer = ContractDeployer(self.web3)
        precomputed_address = deployer.compute_l2_create_address(self.account.address, nonce)
        print(f"precomputed address: {precomputed_address}")

    def test_get_all_account_balances(self):
        balances = self.web3.zksync.zks_get_all_account_balances(self.account.address)
        print(f"balances : {balances}")

    def test_get_confirmed_tokens(self):
        confirmed = self.web3.zksync.zks_get_confirmed_tokens(0, 10)
        print(f"confirmed tokens: {confirmed}")

    def test_is_token_liquid(self):
        """
        ERROR: Method not found under JAVA also
        """
        is_token_liquid = self.web3.zksync.zks_is_token_liquid(self.ETH_TOKEN.l2_address)
        print(f"is_token_liquid: {is_token_liquid}")

    def test_get_token_price(self):
        price = self.web3.zksync.zks_get_token_price(self.ETH_TOKEN.l2_address)
        print(f"price: {price}")

    def test_get_l1_chain_id(self):
        l1_chain_id = self.web3.zksync.zks_l1_chain_id()
        print(f"L1 chain ID: {l1_chain_id} ")

    def test_get_bridge_addresses(self):
        addresses = self.web3.zksync.zks_get_bridge_contracts()
        print(f"Bridge addresses: {addresses}")
