import os
from decimal import Decimal
from unittest import TestCase, skip

from eth_typing import HexStr
from web3 import Web3
from web3.types import TxParams
from web3.middleware import geth_poa_middleware
from zksync2.manage_contracts.contract_deployer import ContractDeployer
from zksync2.manage_contracts.erc20_contract import ERC20FunctionEncoder
from zksync2.manage_contracts.gas_provider import StaticGasProvider
from zksync2.manage_contracts.nonce_holder import NonceHolder
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.manage_contracts.l2_bridge import L2BridgeEncoder
from zksync2.core.types import Token, ZkBlockParams, BridgeAddresses, EthBlockParams
from eth_account import Account
from eth_account.signers.local import LocalAccount

from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.provider.eth_provider import EthereumProvider
from tests.contracts.constructor_contract_utils import ConstructorContractEncoder
from tests.contracts.counter_contract_utils import CounterContractEncoder
from tests.contracts.utils import get_hex_binary
from zksync2.transaction.transaction712 import TxFunctionCall, TxCreateContract, TxCreate2Contract


def generate_random_salt() -> bytes:
    return os.urandom(32)


class ZkSyncWeb3Tests(TestCase):
    GAS_LIMIT = 21000
    ETH_TEST_URL = "https://rpc.ankr.com/eth_goerli"
    ZKSYNC_TEST_URL = "https://zksync2-testnet.zksync.dev"

    ETH_TOKEN = Token.create_eth()
    PRIVATE_KEY = bytes.fromhex("1f0245d47b3a84299aeb121ac33c2dbd1cdb3d3c2079b3240e63796e75ee8b70")
    ETH_AMOUNT_BALANCE = 100
    ETH_TEST_NET_AMOUNT_BALANCE = Decimal(1)

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.ZKSYNC_TEST_URL)
        self.account: LocalAccount = Account.from_key(self.PRIVATE_KEY)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)

        self.gas_provider = StaticGasProvider(Web3.toWei(1, "gwei"), 555000)
        self.CONTRACT_ADDRESS = Web3.toChecksumAddress("0xca9e8bfcd17df56ae90c2a5608e8824dfd021067")

    @skip("Integration test, used for develop purposes only")
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

    @skip("Integration test, used for develop purposes only")
    def test_get_l1_balance(self):
        """
        INFO: For minting use: https://goerli-faucet.pk910.de
        """
        eth_web3 = Web3(Web3.HTTPProvider(self.ETH_TEST_URL))
        eth_balance = eth_web3.eth.get_balance(self.account.address)
        print(f"Eth: balance: {Web3.fromWei(eth_balance, 'ether')}")
        self.assertNotEqual(eth_balance, 0)

    @skip("Integration test, used for develop purposes only")
    def test_get_l2_balance(self):
        zk_balance = self.web3.zksync.get_balance(self.account.address, EthBlockParams.LATEST.value)
        print(f"ZkSync balance: {zk_balance}")

    @skip("Integration test, used for develop purposes only")
    def test_deposit(self):
        print(f"gas price: {self.web3.eth.gas_price}")
        eth_web3 = Web3(Web3.HTTPProvider(self.ETH_TEST_URL))
        eth_web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        eth_provider = EthereumProvider.build_ethereum_provider(zksync=self.web3,
                                                                eth=eth_web3,
                                                                account=self.account,
                                                                gas_provider=self.gas_provider)
        tx_receipt = eth_provider.deposit(self.ETH_TOKEN,
                                          eth_web3.toWei(self.ETH_TEST_NET_AMOUNT_BALANCE, "ether"),
                                          self.account.address)
        self.assertEqual(1, tx_receipt["status"])

    @skip("Integration test, used for develop purposes only")
    def test_get_nonce(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value)
        print(f"Nonce: {nonce}")

    @skip("Integration test, used for develop purposes only")
    def test_get_deployment_nonce(self):
        nonce_holder = NonceHolder(self.web3, self.account)
        print(f"Deployment nonce: {nonce_holder.get_deployment_nonce(self.account.address)}")

    @skip("Integration test, used for develop purposes only")
    def test_get_transaction_receipt(self):
        tx_hash = '0xa645ee8ab4e827a6695f205d8e75afdf97f28d2822b449f9803b986b81e877bc'
        receipt = self.web3.zksync.get_transaction_receipt(tx_hash)
        print(f"receipt: {receipt}")

    @skip("Integration test, used for develop purposes only")
    def test_get_transaction(self):
        tx_hash = '0xa645ee8ab4e827a6695f205d8e75afdf97f28d2822b449f9803b986b81e877bc'
        tx = self.web3.zksync.get_transaction(tx_hash)
        print(f"transaction nonce: {tx['nonce']}")

    @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_transfer_native(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        gas_price = self.web3.zksync.gas_price
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=self.account.address,
                                   gas_limit=0,
                                   gas_price=gas_price)

        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        print(f"test_estimate_gas_transfer_native, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_gas_transfer_native, estimate_gas must be greater 0")

    @skip("Integration test, used for develop purposes only")
    def test_estimate_fee_transfer_native(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        gas_price = self.web3.zksync.gas_price

        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=self.account.address,
                                   gas_limit=0,
                                   gas_price=gas_price)
        estimated_fee = self.web3.zksync.zks_estimate_fee(func_call.tx)
        print(f"Estimated fee: {estimated_fee}")

    @skip("Integration test, used for develop purposes only")
    def test_transfer_native_to_self(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        gas_price = self.web3.zksync.gas_price
        tx_func_call = TxFunctionCall(chain_id=self.chain_id,
                                      nonce=nonce,
                                      from_=self.account.address,
                                      to=self.account.address,
                                      value=Web3.toWei(0.01, 'ether'),
                                      data=HexStr("0x"),
                                      gas_limit=0,  # UNKNOWN AT THIS STATE
                                      gas_price=gas_price,
                                      max_priority_fee_per_gas=100000000)
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx_func_call.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = tx_func_call.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

    @skip("Integration test, used for develop purposes only")
    def test_transfer_token_to_self(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        tokens = self.web3.zksync.zks_get_confirmed_tokens(0, 100)
        not_eth_tokens = [x for x in tokens if not x.is_eth()]
        self.assertTrue(bool(not_eth_tokens), "Can't get non eth tokens")
        token_address = not_eth_tokens[0].l2_address

        erc20_encoder = ERC20FunctionEncoder(self.web3)
        transfer_params = [self.account.address, 0]
        call_data = erc20_encoder.encode_method("transfer", args=transfer_params)

        gas_price = self.web3.zksync.gas_price
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=token_address,
                                   data=call_data,
                                   gas_limit=0,  # UNKNOWN AT THIS STATE
                                   gas_price=gas_price,
                                   max_priority_fee_per_gas=100000000)

        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")
        tx_712 = func_call.tx712(estimated_gas=estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

    @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_withdraw(self):
        bridges = self.web3.zksync.zks_get_bridge_contracts()
        l2_func_encoder = L2BridgeEncoder(self.web3)
        call_data = l2_func_encoder.encode_function(fn_name="withdraw", args=[
            self.account.address,
            self.ETH_TOKEN.l2_address,
            self.ETH_TOKEN.to_int(Decimal("0.001"))
        ])
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)

        gas_price = self.web3.zksync.gas_price
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=bridges.l2_eth_default_bridge,
                                   data=call_data,
                                   gas_limit=0,
                                   gas_price=gas_price)
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        print(f"test_estimate_gas_withdraw, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_gas_withdraw, estimate_gas must be greater 0")

    @skip("Integration test, used for develop purposes only")
    def test_withdraw(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        bridges: BridgeAddresses = self.web3.zksync.zks_get_bridge_contracts()

        l2_func_encoder = L2BridgeEncoder(self.web3)
        call_data = l2_func_encoder.encode_function(fn_name="withdraw", args=[
            self.account.address,
            self.ETH_TOKEN.l2_address,
            self.ETH_TOKEN.to_int(Decimal("0.001"))
        ])

        gas_price = self.web3.zksync.gas_price
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=bridges.l2_eth_default_bridge,
                                   data=HexStr(call_data),
                                   gas_limit=0,
                                   gas_price=gas_price,
                                   max_priority_fee_per_gas=100000000)
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")
        tx_712 = func_call.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

    @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_execute(self):
        erc20func_encoder = ERC20FunctionEncoder(self.web3)
        transfer_args = [
            Web3.toChecksumAddress("0xe1fab3efd74a77c23b426c302d96372140ff7d0c"),
            1
        ]
        call_data = erc20func_encoder.encode_method(fn_name="transfer", args=transfer_args)
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        gas_price = self.web3.zksync.gas_price

        to_addr = Web3.toChecksumAddress("0x79f73588fa338e685e9bbd7181b410f60895d2a3")
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=to_addr,
                                   data=HexStr(call_data),
                                   gas_limit=0,
                                   gas_price=gas_price)
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        print(f"test_estimate_gas_execute, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_withdraw, estimate_gas must be greater 0")

    @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_deploy_contract(self):
        counter_contract_bin = get_hex_binary("counter_contract.hex")
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price
        create2_contract = TxCreate2Contract(web3=self.web3,
                                             chain_id=self.chain_id,
                                             nonce=nonce,
                                             from_=self.account.address,
                                             gas_limit=0,
                                             gas_price=gas_price,
                                             bytecode=counter_contract_bin)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)
        print(f"test_estimate_gas_deploy_contract, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_gas_deploy_contract, estimate_gas must be greater 0")

    @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_create(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        nonce_holder = NonceHolder(self.web3, self.account)
        deployment_nonce = nonce_holder.get_deployment_nonce(self.account.address)
        deployer = ContractDeployer(self.web3)
        precomputed_address = deployer.compute_l2_create_address(self.account.address, deployment_nonce)

        print(f"precomputed address: {precomputed_address}")

        gas_price = self.web3.zksync.gas_price
        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,  # UNKNOWN AT THIS STATE
                                           gas_price=gas_price,
                                           bytecode=get_hex_binary("counter_contract.hex"),
                                           salt=random_salt)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")
        tx_712 = create_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])
        contract_address = tx_receipt["contractAddress"]
        print(f"contract address: {contract_address}")
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

        counter_contract_encoder = CounterContractEncoder(self.web3)
        call_data = counter_contract_encoder.encode_method(fn_name="get", args=[])
        eth_tx: TxParams = {
            "from": self.account.address,
            "to": contract_address,
            "data": call_data
        }
        eth_ret = self.web3.zksync.call(eth_tx, ZkBlockParams.COMMITTED.value)
        # INFO: type dependent cast, signature of calling function must be known
        result = int.from_bytes(eth_ret, "big", signed=True)
        print(f"Call method for deployed contract, address: {contract_address}, value: {result}")

    @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_constructor_create(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price

        nonce_holder = NonceHolder(self.web3, self.account)
        deployment_nonce = nonce_holder.get_deployment_nonce(self.account.address)

        deployer = ContractDeployer(self.web3)
        precomputed_address = deployer.compute_l2_create_address(self.account.address, deployment_nonce)

        constructor_encoder = ConstructorContractEncoder(self.web3)
        encoded_ctor = constructor_encoder.encode_constructor(a=42, b=43, shouldRevert=False)

        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,  # UNKNOWN AT THIS STATE,
                                           gas_price=gas_price,
                                           bytecode=constructor_encoder.bytecode,
                                           call_data=encoded_ctor,
                                           salt=random_salt)

        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)

        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = create_contract.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

        contract_address = tx_receipt["contractAddress"]
        print(f"contract address: {contract_address}")
        # INFO: does not work, contract_address is None
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

        call_data = constructor_encoder.encode_method(fn_name="get", args=[])
        eth_tx: TxParams = {
            "from": self.account.address,
            "to": contract_address,
            "data": call_data
        }
        eth_ret = self.web3.zksync.call(eth_tx, ZkBlockParams.COMMITTED.value)
        # INFO: type dependent cast, signature of calling function must be known
        result = int.from_bytes(eth_ret, "big", signed=True)
        print(f"Call method for deployed contract, address: {contract_address}, value: {result}")

    @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_create2(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price
        deployer = ContractDeployer(self.web3)
        counter_contract_bin = get_hex_binary("counter_contract.hex")
        precomputed_address = deployer.compute_l2_create2_address(sender=self.account.address,
                                                                  bytecode=counter_contract_bin,
                                                                  constructor=b'',
                                                                  salt=random_salt)
        create2_contract = TxCreate2Contract(web3=self.web3,
                                             chain_id=self.chain_id,
                                             nonce=nonce,
                                             from_=self.account.address,
                                             gas_limit=0,
                                             gas_price=gas_price,
                                             bytecode=counter_contract_bin,
                                             salt=random_salt)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = create2_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=1.0)

        self.assertEqual(1, tx_receipt["status"])

        contract_address = tx_receipt["contractAddress"]
        print(f"contract address: {contract_address}")
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

        counter_contract_encoder = CounterContractEncoder(self.web3)
        call_data = counter_contract_encoder.encode_method(fn_name="get", args=[])
        eth_tx: TxParams = {
            "from": self.account.address,
            "to": contract_address,
            "data": call_data
        }
        eth_ret = self.web3.zksync.call(eth_tx, ZkBlockParams.COMMITTED.value)
        result = int.from_bytes(eth_ret, "big", signed=True)
        print(f"Call method for deployed contract, address: {contract_address}, value: {result}")

    @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_deps_create(self):
        random_salt = generate_random_salt()
        foo = get_hex_binary("foo.hex")
        foo_deps = get_hex_binary("foo_deps.hex")
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price
        nonce_holder = NonceHolder(self.web3, self.account)
        deployment_nonce = nonce_holder.get_deployment_nonce(self.account.address)
        contract_deployer = ContractDeployer(self.web3)
        precomputed_address = contract_deployer.compute_l2_create_address(self.account.address,
                                                                          deployment_nonce)

        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,
                                           gas_price=gas_price,
                                           bytecode=foo,
                                           deps=[foo_deps],
                                           salt=random_salt)

        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = create_contract.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

        contract_address = contract_deployer.extract_contract_address(tx_receipt)
        print(f"contract address: {contract_address}")
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

    @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_deps_create2(self):
        random_salt = generate_random_salt()
        foo = get_hex_binary("foo.hex")
        foo_deps = get_hex_binary("foo_deps.hex")
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price

        contract_deployer = ContractDeployer(self.web3)
        precomputed_address = contract_deployer.compute_l2_create2_address(self.account.address,
                                                                           bytecode=foo,
                                                                           constructor=b'',
                                                                           salt=random_salt)
        create2_contract = TxCreate2Contract(web3=self.web3,
                                             chain_id=self.chain_id,
                                             nonce=nonce,
                                             from_=self.account.address,
                                             gas_limit=0,
                                             gas_price=gas_price,
                                             bytecode=foo,
                                             deps=[foo_deps],
                                             salt=random_salt)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = create2_contract.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])
        contract_address = contract_deployer.extract_contract_address(tx_receipt)
        print(f"contract address: {contract_address}")
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

    @skip("Integration test, used for develop purposes only")
    def test_execute_contract(self):
        # TODO: link to another test for getting right contract address
        self.CONTRACT_ADDRESS = HexStr("0xfc2037739c537CCAf5F184eb105B69cA612a208F")

        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        counter_contract_encoder = CounterContractEncoder(self.web3)
        encoded_get = counter_contract_encoder.encode_method(fn_name="get", args=[])
        eth_tx: TxParams = {
            "from": self.account.address,
            "to": self.CONTRACT_ADDRESS,
            "data": encoded_get,
        }
        eth_ret = self.web3.zksync.call(eth_tx, ZkBlockParams.COMMITTED.value)
        result = int.from_bytes(eth_ret, "big", signed=True)
        gas_price = self.web3.zksync.gas_price

        call_data = counter_contract_encoder.encode_method(fn_name="increment", args=[1])
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=self.CONTRACT_ADDRESS,
                                   data=call_data,
                                   gas_limit=0,  # UNKNOWN AT THIS STATE,
                                   gas_price=gas_price)
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = func_call.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

        eth_ret2 = self.web3.zksync.call(eth_tx, ZkBlockParams.COMMITTED.value)
        updated_result = int.from_bytes(eth_ret2, "big", signed=True)
        self.assertEqual(result + 1, updated_result)

    @skip("Integration test, used for develop purposes only")
    def test_get_all_account_balances(self):
        balances = self.web3.zksync.zks_get_all_account_balances(self.account.address)
        print(f"balances : {balances}")

    @skip("Integration test, used for develop purposes only")
    def test_get_confirmed_tokens(self):
        confirmed = self.web3.zksync.zks_get_confirmed_tokens(0, 10)
        print(f"confirmed tokens: {confirmed}")

    @skip("Integration test, used for develop purposes only")
    def test_get_token_price(self):
        price = self.web3.zksync.zks_get_token_price(self.ETH_TOKEN.l2_address)
        print(f"price: {price}")

    @skip("Integration test, used for develop purposes only")
    def test_get_l1_chain_id(self):
        l1_chain_id = self.web3.zksync.zks_l1_chain_id()
        print(f"L1 chain ID: {l1_chain_id} ")

    @skip("Integration test, used for develop purposes only")
    def test_get_bridge_addresses(self):
        addresses = self.web3.zksync.zks_get_bridge_contracts()
        print(f"Bridge addresses: {addresses}")
