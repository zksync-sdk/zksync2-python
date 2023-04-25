import os
from decimal import Decimal
from unittest import TestCase, skip
from eth_typing import HexStr
from web3 import Web3
from web3.types import TxParams
from web3.middleware import geth_poa_middleware
from zksync2.core.utils import to_bytes
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.manage_contracts.contract_factory import LegacyContractFactory
from zksync2.manage_contracts.erc20_contract import ERC20Encoder, ERC20Contract
from zksync2.manage_contracts.nonce_holder import NonceHolder
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.core.types import Token, ZkBlockParams, EthBlockParams, ADDRESS_DEFAULT
from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.provider.eth_provider import EthereumProvider
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from tests.contracts.utils import contract_path
from zksync2.transaction.transaction_builders import TxFunctionCall, TxCreateContract, TxCreate2Contract, TxWithdraw
from test_config import LOCAL_ENV, EnvType, EnvPrivateKey


def generate_random_salt() -> bytes:
    return os.urandom(32)


class ZkSyncWeb3Tests(TestCase):
    ETH_TOKEN = Token.create_eth()
    ETH_TEST_NET_AMOUNT_BALANCE = Decimal(1)

    def setUp(self) -> None:
        self.env = LOCAL_ENV
        self.web3 = ZkSyncBuilder.build(self.env.zksync_server)
        env_key = EnvPrivateKey("ZKSYNC_KEY1")
        self.account: LocalAccount = Account.from_key(env_key.key)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.counter_address = None
        self.test_tx_hash = None
        # INFO: use deploy_erc20_token_builder to get new address
        if self.env.type == EnvType.LOCAL_HOST:
            self.some_erc20_address = Web3.to_checksum_address("0x37b96512962FC7773E06237116BE693Eb2b3cD51")
        if self.env.type == EnvType.TESTNET:
            # https://goerli.explorer.zksync.io/address/0xd782e03F4818A7eDb0bc5f70748F67B4e59CdB33#contract
            self.some_erc20_address = Web3.to_checksum_address("0xd782e03F4818A7eDb0bc5f70748F67B4e59CdB33")
        self.ERC20_Token = Token(l1_address=ADDRESS_DEFAULT,
                                 l2_address=self.some_erc20_address,
                                 symbol="SERC20",
                                 decimals=18)

    @skip("Integration test, used for develop purposes only")
    def test_send_money(self):
        gas_limit = 21000
        web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        account = web3.eth.accounts[0]
        transaction: TxParams = {
            "from": account,
            "gasPrice": Web3.to_wei(1, "gwei"),
            "gas": gas_limit,
            "to": self.account.address,
            "value": web3.to_wei(1000000, 'ether')
        }
        tx_hash = web3.eth.send_transaction(transaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(txn_receipt['status'], 1)

    # @skip("Integration test, used for develop purposes only")
    def test_get_l1_balance(self):
        """
        INFO: For minting use: https://goerli-faucet.pk910.de
        """
        eth_web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        eth_balance = eth_web3.eth.get_balance(self.account.address)
        print(f"Eth: balance: {Web3.from_wei(eth_balance, 'ether')}")
        self.assertNotEqual(eth_balance, 0)

    # @skip("Integration test, used for develop purposes only")
    def test_get_l2_balance(self):
        zk_balance = self.web3.zksync.get_balance(self.account.address, EthBlockParams.LATEST.value)
        print(f"ZkSync balance: {zk_balance}")
        print(f"In Ether: {Web3.from_wei(zk_balance, 'ether')}")

    # @skip("Integration test, used for develop purposes only")
    def test_get_nonce(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value)
        print(f"Nonce: {nonce}")

    # @skip("Integration test, used for develop purposes only")
    def test_get_deployment_nonce(self):
        nonce_holder = NonceHolder(self.web3, self.account)
        print(f"Deployment nonce: {nonce_holder.get_deployment_nonce(self.account.address)}")

    # @skip("Integration test, used for develop purposes only")
    def test_get_transaction_receipt(self):
        if self.test_tx_hash is None:
            nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
            gas_price = self.web3.zksync.gas_price
            tx_func_call = TxFunctionCall(chain_id=self.chain_id,
                                          nonce=nonce,
                                          from_=self.account.address,
                                          to=self.account.address,
                                          value=Web3.to_wei(0.01, 'ether'),
                                          data=HexStr("0x"),
                                          gas_limit=0,  # UNKNOWN AT THIS STATE
                                          gas_price=gas_price,
                                          max_priority_fee_per_gas=100000000)
            estimate_gas = self.web3.zksync.eth_estimate_gas(tx_func_call.tx)
            print(f"Fee for transaction is: {estimate_gas * gas_price}")

            tx_712 = tx_func_call.tx712(estimate_gas)
            singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
            msg = tx_712.encode(singed_message)
            self.test_tx_hash = self.web3.zksync.send_raw_transaction(msg)
            self.web3.zksync.wait_for_transaction_receipt(self.test_tx_hash)
        receipt = self.web3.zksync.get_transaction_receipt(self.test_tx_hash)
        print(f"receipt: {receipt['blockHash'].hex()}")

    # @skip("Integration test, used for develop purposes only")
    def test_get_transaction(self):
        if self.test_tx_hash is None:
            nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
            gas_price = self.web3.zksync.gas_price
            tx_func_call = TxFunctionCall(chain_id=self.chain_id,
                                          nonce=nonce,
                                          from_=self.account.address,
                                          to=self.account.address,
                                          value=Web3.to_wei(0.01, 'ether'),
                                          data=HexStr("0x"),
                                          gas_limit=0,  # UNKNOWN AT THIS STATE
                                          gas_price=gas_price,
                                          max_priority_fee_per_gas=100000000)
            estimate_gas = self.web3.zksync.eth_estimate_gas(tx_func_call.tx)
            print(f"Fee for transaction is: {estimate_gas * gas_price}")

            tx_712 = tx_func_call.tx712(estimate_gas)
            singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
            msg = tx_712.encode(singed_message)
            self.test_tx_hash = self.web3.zksync.send_raw_transaction(msg)
            self.web3.zksync.wait_for_transaction_receipt(self.test_tx_hash)
        tx = self.web3.zksync.get_transaction(self.test_tx_hash)
        self.assertEqual(tx['from'], self.account.address)

    # @skip("Integration test, used for develop purposes only")
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

    # @skip("Integration test, used for develop purposes only")
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

    # @skip("Integration test, used for develop purposes only")
    def test_transfer_native_to_self(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        gas_price = self.web3.zksync.gas_price
        tx_func_call = TxFunctionCall(chain_id=self.chain_id,
                                      nonce=nonce,
                                      from_=self.account.address,
                                      to=self.account.address,
                                      value=Web3.to_wei(0.01, 'ether'),
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

    def deploy_erc20_token_builder(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        counter_contract = ContractEncoder.from_json(self.web3, contract_path("SomeERC20.json"))
        random_salt = generate_random_salt()
        gas_price = self.web3.zksync.gas_price
        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,  # UNKNOWN AT THIS STATE
                                           gas_price=gas_price,
                                           bytecode=counter_contract.bytecode,
                                           salt=random_salt)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")
        tx_712 = create_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt['status'])
        contract_address = tx_receipt["contractAddress"]
        if self.some_erc20_address is None:
            self.some_erc20_address = contract_address
        print(f"Contract: {contract_address}")

    def mint_some_erc20(self, amount: int):
        some_erc20_encoder = ContractEncoder.from_json(self.web3, contract_path("SomeERC20.json"))
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value)
        gas_price = self.web3.zksync.gas_price

        args = (self.account.address, self.ERC20_Token.to_int(amount))
        call_data = some_erc20_encoder.encode_method(fn_name='mint', args=args)
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=self.some_erc20_address,
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
        self.assertEqual(1, tx_receipt['status'])
        print(f"Mint tx status: {tx_receipt['status']}")

    # @skip("Integration test, used for develop purposes only")
    def test_transfer_erc20_token_to_self(self):
        erc20 = ERC20Contract(web3=self.web3.zksync,
                              contract_address=self.some_erc20_address,
                              account=self.account)
        balance_before = erc20.balance_of(self.account.address)
        print(f"{self.ERC20_Token.symbol} balance before : {self.ERC20_Token.format_token(balance_before)}")

        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        token_address = self.ERC20_Token.l2_address

        tokens_amount = 1
        erc20_encoder = ERC20Encoder(self.web3)
        transfer_params = (self.account.address, self.ERC20_Token.to_int(tokens_amount))
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

        balance_after = erc20.balance_of(self.account.address)
        print(f"{self.ERC20_Token.symbol} balance before : {self.ERC20_Token.format_token(balance_after)}")
        self.assertEqual(balance_before, balance_after)

    def test_transfer_erc20_token(self):
        env_bob = EnvPrivateKey("ZKSYNC_KEY2")
        alice = self.account
        bob: LocalAccount = Account.from_key(env_bob.key)

        erc20 = ERC20Contract(web3=self.web3.zksync,
                              contract_address=self.some_erc20_address,
                              account=alice)
        alice_balance_before = erc20.balance_of(alice.address)
        bob_balance_before = erc20.balance_of(bob.address)
        print(f"Alice {self.ERC20_Token.symbol} balance before : {self.ERC20_Token.format_token(alice_balance_before)}")
        print(f"Bob {self.ERC20_Token.symbol} balance before : {self.ERC20_Token.format_token(bob_balance_before)}")

        nonce = self.web3.zksync.get_transaction_count(alice.address, ZkBlockParams.COMMITTED.value)
        token_address = self.ERC20_Token.l2_address

        tokens_amount = 1
        erc20_encoder = ERC20Encoder(self.web3)
        transfer_params = (bob.address, self.ERC20_Token.to_int(tokens_amount))
        call_data = erc20_encoder.encode_method("transfer", args=transfer_params)

        gas_price = self.web3.zksync.gas_price
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=alice.address,
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
        print(f"Tx hash: {tx_receipt['transactionHash'].hex()}")

        alice_balance_after = erc20.balance_of(alice.address)
        bob_balance_after = erc20.balance_of(bob.address)
        print(f"Alice {self.ERC20_Token.symbol} balance before : {self.ERC20_Token.format_token(alice_balance_after)}")
        print(f"Bob {self.ERC20_Token.symbol} balance before : {self.ERC20_Token.format_token(bob_balance_after)}")

        self.assertEqual(bob_balance_after, bob_balance_before + self.ERC20_Token.to_int(tokens_amount))
        self.assertEqual(alice_balance_after, alice_balance_before - self.ERC20_Token.to_int(tokens_amount))

    # @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_withdraw(self):
        withdraw = TxWithdraw(web3=self.web3,
                              token=Token.create_eth(),
                              amount=1,
                              gas_limit=0,  # unknown
                              account=self.account)
        estimated_gas = self.web3.zksync.eth_estimate_gas(withdraw.tx)
        print(f"test_estimate_gas_withdraw, estimate_gas {estimated_gas}")
        self.assertGreater(estimated_gas, 0, "test_estimate_gas_withdraw, estimate_gas must be greater 0")

    # @skip("Integration test, used for develop purposes only")
    def test_withdraw(self):
        amount = 0.1
        eth_web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        eth_web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        eth_balance = eth_web3.eth.get_balance(self.account.address)
        print(f"Eth: balance: {Web3.from_wei(eth_balance, 'ether')}")

        eth_provider = EthereumProvider(self.web3,
                                        eth_web3,
                                        self.account)

        withdraw = TxWithdraw(web3=self.web3,
                              token=Token.create_eth(),
                              amount=Web3.to_wei(amount, "ether"),
                              gas_limit=0,  # unknown
                              account=self.account)
        estimated_gas = self.web3.zksync.eth_estimate_gas(withdraw.tx)
        tx = withdraw.estimated_gas(estimated_gas)
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.zksync.send_raw_transaction(signed.rawTransaction)
        zks_receipt = self.web3.zksync.wait_finalized(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, zks_receipt['status'])

        tx_receipt = eth_provider.finalize_withdrawal(zks_receipt["transactionHash"])
        self.assertEqual(1, tx_receipt['status'])
        print(f"Status: {tx_receipt['status']}")

        prev = eth_balance
        eth_balance = eth_web3.eth.get_balance(self.account.address)
        print(f"Eth: balance: {Web3.from_wei(eth_balance, 'ether')}")

        fee = tx_receipt['gasUsed'] * tx_receipt['effectiveGasPrice']
        withdraw_absolute = Web3.to_wei(amount, 'ether') - fee
        diff = eth_balance - prev
        self.assertEqual(withdraw_absolute, diff)
        print(f"Eth diff with fee included: {Web3.from_wei(diff, 'ether')}")

    # @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_execute(self):
        erc20func_encoder = ERC20Encoder(self.web3)
        transfer_args = (
            Web3.to_checksum_address("0xe1fab3efd74a77c23b426c302d96372140ff7d0c"),
            1
        )
        call_data = erc20func_encoder.encode_method(fn_name="transfer", args=transfer_args)
        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
        gas_price = self.web3.zksync.gas_price

        call_data_bytes = to_bytes(call_data)
        print(f"Call data length: {len(call_data_bytes)}")

        to_addr = Web3.to_checksum_address("0x79f73588fa338e685e9bbd7181b410f60895d2a3")
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

    # @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_deploy_contract(self):
        counter_contract = ContractEncoder.from_json(self.web3, contract_path("Counter.json"))
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price
        create2_contract = TxCreate2Contract(web3=self.web3,
                                             chain_id=self.chain_id,
                                             nonce=nonce,
                                             from_=self.account.address,
                                             gas_limit=0,
                                             gas_price=gas_price,
                                             bytecode=counter_contract.bytecode)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)
        print(f"test_estimate_gas_deploy_contract, estimate_gas: {estimate_gas}")
        self.assertGreater(estimate_gas, 0, "test_estimate_gas_deploy_contract, estimate_gas must be greater 0")

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_create(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        nonce_holder = NonceHolder(self.web3, self.account)
        deployment_nonce = nonce_holder.get_deployment_nonce(self.account.address)
        deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = deployer.compute_l2_create_address(self.account.address, deployment_nonce)
        counter_contract = ContractEncoder.from_json(self.web3, contract_path("Counter.json"))

        print(f"precomputed address: {precomputed_address}")

        gas_price = self.web3.zksync.gas_price
        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,  # UNKNOWN AT THIS STATE
                                           gas_price=gas_price,
                                           bytecode=counter_contract.bytecode,
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
        self.counter_address = contract_address

        print(f"contract address: {contract_address}")
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

        value = counter_contract.contract.functions.get().call(
            {
                "from": self.account.address,
                "to": contract_address
            })
        self.assertEqual(0, value)
        print(f"Call method for deployed contract, address: {contract_address}, value: {value}")

    @skip("web3py 6.0.0 does not provide protocol version")
    def test_protocol_version(self):
        version = self.web3.zksync.protocol_version
        print(f"Protocol version: {version}")
        self.assertEqual(version, "zks/1")

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_constructor_create(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price

        nonce_holder = NonceHolder(self.web3, self.account)
        deployment_nonce = nonce_holder.get_deployment_nonce(self.account.address)

        deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = deployer.compute_l2_create_address(self.account.address, deployment_nonce)

        constructor_encoder = ContractEncoder.from_json(self.web3, contract_path("SimpleConstructor.json"))
        a = 2
        b = 3
        encoded_ctor = constructor_encoder.encode_constructor(a=a, b=b, shouldRevert=False)

        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,  # UNKNOWN AT THIS STATE,
                                           gas_price=gas_price,
                                           bytecode=constructor_encoder.bytecode,
                                           call_data=encoded_ctor
                                           , salt=random_salt)

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

        value = constructor_encoder.contract.functions.get().call(
            {
                "from": self.account.address,
                "to": contract_address
            })
        self.assertEqual(a * b, value)
        print(f"Call method for deployed contract, address: {contract_address}, value: {value}")

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_create2(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price
        deployer = PrecomputeContractDeployer(self.web3)

        counter_contract_encoder = ContractEncoder.from_json(self.web3, contract_path("Counter.json"))
        precomputed_address = deployer.compute_l2_create2_address(sender=self.account.address,
                                                                  bytecode=counter_contract_encoder.bytecode,
                                                                  constructor=b'',
                                                                  salt=random_salt)
        create2_contract = TxCreate2Contract(web3=self.web3,
                                             chain_id=self.chain_id,
                                             nonce=nonce,
                                             from_=self.account.address,
                                             gas_limit=0,
                                             gas_price=gas_price,
                                             bytecode=counter_contract_encoder.bytecode,
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
        self.counter_address = contract_address

        print(f"contract address: {contract_address}")
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

        value = counter_contract_encoder.contract.functions.get().call(
            {
                "from": self.account.address,
                "to": contract_address
            })
        self.assertEqual(0, value)
        print(f"Call method for deployed contract, address: {contract_address}, value: {value}")

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_deps_create(self):
        random_salt = generate_random_salt()
        import_contract = ContractEncoder.from_json(self.web3, contract_path("Import.json"))
        import_dependency_contract = ContractEncoder.from_json(self.web3, contract_path("Foo.json"))
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price
        nonce_holder = NonceHolder(self.web3, self.account)
        deployment_nonce = nonce_holder.get_deployment_nonce(self.account.address)
        contract_deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = contract_deployer.compute_l2_create_address(self.account.address,
                                                                          deployment_nonce)

        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,
                                           gas_price=gas_price,
                                           bytecode=import_contract.bytecode,
                                           deps=[import_dependency_contract.bytecode],
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

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_deps_create2(self):
        random_salt = generate_random_salt()
        import_contract = ContractEncoder.from_json(self.web3, contract_path("Import.json"))
        import_dependency_contract = ContractEncoder.from_json(self.web3, contract_path("Foo.json"))
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price

        contract_deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = contract_deployer.compute_l2_create2_address(self.account.address,
                                                                           bytecode=import_contract.bytecode,
                                                                           constructor=b'',
                                                                           salt=random_salt)
        create2_contract = TxCreate2Contract(web3=self.web3,
                                             chain_id=self.chain_id,
                                             nonce=nonce,
                                             from_=self.account.address,
                                             gas_limit=0,
                                             gas_price=gas_price,
                                             bytecode=import_contract.bytecode,
                                             deps=[import_dependency_contract.bytecode],
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

    # @skip("Integration test, used for develop purposes only")
    def test_execute_contract(self):
        counter_contract = ContractEncoder.from_json(self.web3, contract_path("Counter.json"))
        if self.counter_address is None:
            random_salt = generate_random_salt()
            nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
            gas_price = self.web3.zksync.gas_price
            create_contract = TxCreateContract(web3=self.web3,
                                               chain_id=self.chain_id,
                                               nonce=nonce,
                                               from_=self.account.address,
                                               gas_limit=0,  # UNKNOWN AT THIS STATE
                                               gas_price=gas_price,
                                               bytecode=counter_contract.bytecode,
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
            self.counter_address = contract_address

        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value)
        encoded_get = counter_contract.encode_method(fn_name="get", args=[])
        eth_tx: TxParams = {
            "from": self.account.address,
            "to": self.counter_address,
            "data": encoded_get,
        }
        eth_ret = self.web3.zksync.call(eth_tx, EthBlockParams.LATEST.value)
        result = int.from_bytes(eth_ret, "big", signed=True)
        gas_price = self.web3.zksync.gas_price

        call_data = counter_contract.encode_method(fn_name="increment", args=[1])
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=self.counter_address,
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

        eth_ret2 = self.web3.zksync.call(eth_tx, EthBlockParams.LATEST.value)
        updated_result = int.from_bytes(eth_ret2, "big", signed=True)
        self.assertEqual(result + 1, updated_result)

    def test_contract_factory(self):
        increment_value = 10
        salt = generate_random_salt()
        deployer = LegacyContractFactory.from_json(zksync=self.web3,
                                                   compiled_contract=contract_path("Counter.json"),
                                                   account=self.account,
                                                   signer=self.signer)
        contract = deployer.deploy(salt=salt)
        value = contract.functions.get().call({
            "from": self.account.address
        })
        print(f"Value: {value}")

        gas_price = self.web3.zksync.gas_price
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value)
        tx = contract.functions.increment(increment_value).build_transaction({
            "nonce": nonce,
            "from": self.account.address,
            # INFO: this fields can't be got automatically because internally
            #      web3 py uses web3.eth provider with specific lambdas for getting them
            "maxPriorityFeePerGas": 1000000,
            "maxFeePerGas": gas_price
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.zksync.send_raw_transaction(signed.rawTransaction)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(1, tx_receipt['status'])

        value = contract.functions.get().call(
            {
                "from": self.account.address,
            })
        print(f"Value: {value}")
        self.assertEqual(increment_value, value)

    # @skip("Integration test, used for develop purposes only")
    def test_get_all_account_balances(self):
        balances = self.web3.zksync.zks_get_all_account_balances(self.account.address)
        print(f"balances : {balances}")

    # @skip("Integration test, used for develop purposes only")
    def test_get_confirmed_tokens(self):
        confirmed = self.web3.zksync.zks_get_confirmed_tokens(0, 100)
        print(f"confirmed tokens: {confirmed}")
        for token in confirmed:
            if token.is_eth():
                balance = self.web3.zksync.get_balance(self.account.address)
            else:
                erc20 = ERC20Contract(web3=self.web3.zksync,
                                      contract_address=token.l2_address,
                                      account=self.account)
                balance = erc20.balance_of(self.account.address)
            print(f"Token {token.symbol} : {balance}")

    # @skip("Integration test, used for develop purposes only")
    def test_get_token_price(self):
        price = self.web3.zksync.zks_get_token_price(self.ETH_TOKEN.l2_address)
        print(f"price: {price}")

    # @skip("Integration test, used for develop purposes only")
    def test_get_l1_chain_id(self):
        l1_chain_id = self.web3.zksync.zks_l1_chain_id()
        print(f"L1 chain ID: {l1_chain_id} ")

    # @skip("Integration test, used for develop purposes only")
    def test_get_bridge_addresses(self):
        addresses = self.web3.zksync.zks_get_bridge_contracts()
        print(f"Bridge addresses: {addresses}")
