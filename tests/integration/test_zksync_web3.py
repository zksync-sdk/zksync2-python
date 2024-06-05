import os
from decimal import Decimal
from pathlib import Path
from unittest import TestCase, skip

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from eth_utils import keccak
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import TxParams

from tests.contracts.utils import contract_path
from zksync2.core.types import (
    Token,
    ZkBlockParams,
    EthBlockParams,
    ADDRESS_DEFAULT,
    StorageProof,
)
from zksync2.core.utils import pad_front_bytes, to_bytes, pad_back_bytes, L2_BASE_TOKEN_ADDRESS
from zksync2.manage_contracts.contract_encoder_base import (
    ContractEncoder,
    JsonConfiguration,
)
from zksync2.manage_contracts.contract_factory import LegacyContractFactory
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.precompute_contract_deployer import (
    PrecomputeContractDeployer,
)
from zksync2.manage_contracts.utils import nonce_holder_abi_default
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.module.request_types import Transaction, EIP712Meta
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import (
    TxFunctionCall,
    TxCreateContract,
    TxCreate2Contract,
)
from .test_config import LOCAL_ENV, EnvType


def generate_random_salt() -> bytes:
    return os.urandom(32)


class ZkSyncWeb3Tests(TestCase):
    ETH_TOKEN = Token.create_eth()
    ETH_TEST_NET_AMOUNT_BALANCE = Decimal(1)

    def setUp(self) -> None:
        self.env = LOCAL_ENV
        self.web3 = ZkSyncBuilder.build(self.env.zksync_server)
        self.account: LocalAccount = Account.from_key(
            "7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110"
        )
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.counter_address = None
        self.test_tx_hash = None
        # INFO: use deploy_erc20_token_builder to get new address
        if self.env.type == EnvType.LOCAL_HOST:
            self.some_erc20_address = Web3.to_checksum_address(
                "0x37b96512962FC7773E06237116BE693Eb2b3cD51"
            )
        if self.env.type == EnvType.TESTNET:
            # https://goerli.explorer.zksync.io/address/0xd782e03F4818A7eDb0bc5f70748F67B4e59CdB33#contract
            self.some_erc20_address = Web3.to_checksum_address(
                "0xd782e03F4818A7eDb0bc5f70748F67B4e59CdB33"
            )
        self.ERC20_Token = Token(
            l1_address=ADDRESS_DEFAULT,
            l2_address=self.some_erc20_address,
            symbol="SERC20",
            decimals=18,
        )

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
            "value": web3.to_wei(1000000, "ether"),
        }
        tx_hash = web3.eth.send_transaction(transaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(txn_receipt["status"], 1)

    def test_zks_l1_batch_number(self):
        result = self.web3.zksync.zks_l1_batch_number()
        self.assertGreater(result, 0)

    def test_zks_get_l1_batch_block_range(self):
        l1_batch_number = self.web3.zksync.zks_l1_batch_number()
        result = self.web3.zksync.zks_get_l1_batch_block_range(l1_batch_number)
        self.assertIsNotNone(result)

    @skip
    def test_zks_get_l1_batch_details(self):
        l1_batch_number = self.web3.zksync.zks_l1_batch_number()
        result = self.web3.zksync.zks_get_l1_batch_details(l1_batch_number)
        self.assertIsNotNone(result)

    def test_zks_estimate_gas_l1_to_l2(self):
        meta = EIP712Meta(gas_per_pub_data=800)
        result = self.web3.zksync.zks_estimate_gas_l1_to_l2(
            {
                "from": self.account.address,
                "to": self.web3.zksync.zks_main_contract(),
                "value": 7_000_000_000,
                "eip712Meta": meta,
            }
        )
        self.assertIsNotNone(result)

    def test_zks_get_proof(self):
        address_padded = pad_front_bytes(to_bytes(self.account.address), 32)

        concatenated = pad_back_bytes(address_padded, 64)

        storage_key = keccak(concatenated).hex()

        l1_batch_number = self.web3.zksync.zks_l1_batch_number()
        try:
            result: StorageProof = self.web3.zksync.zks_get_proof(
                ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value,
                [storage_key],
                l1_batch_number,
            )
            self.assertIsNotNone(result)
        except:
            pass

    # @skip("Integration test, used for develop purposes only")
    def test_get_l1_balance(self):
        eth_web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        eth_balance = eth_web3.eth.get_balance(self.account.address)
        self.assertNotEqual(eth_balance, 0)

    # @skip("Integration test, used for develop purposes only")
    def test_get_l2_balance(self):
        zk_balance = self.web3.zksync.get_balance(
            self.account.address, EthBlockParams.LATEST.value
        )

    # @skip("Integration test, used for develop purposes only")
    def test_get_nonce(self):
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.LATEST.value
        )

    # @skip("Integration test, used for develop purposes only")
    def test_get_transaction_receipt(self):
        if self.test_tx_hash is None:
            nonce = self.web3.zksync.get_transaction_count(
                self.account.address, ZkBlockParams.COMMITTED.value
            )
            gas_price = self.web3.zksync.gas_price
            tx_func_call = TxFunctionCall(
                chain_id=self.chain_id,
                nonce=nonce,
                from_=self.account.address,
                to=self.account.address,
                value=Web3.to_wei(0.01, "ether"),
                data=HexStr("0x"),
                gas_limit=0,  # UNKNOWN AT THIS STATE
                gas_price=gas_price,
                max_priority_fee_per_gas=100000000,
            )
            estimate_gas = self.web3.zksync.eth_estimate_gas(tx_func_call.tx)

            tx_712 = tx_func_call.tx712(estimate_gas)
            singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
            msg = tx_712.encode(singed_message)
            self.test_tx_hash = self.web3.zksync.send_raw_transaction(msg)
            self.web3.zksync.wait_for_transaction_receipt(self.test_tx_hash)
        receipt = self.web3.zksync.get_transaction_receipt(self.test_tx_hash)

    # @skip("Integration test, used for develop purposes only")
    def test_get_transaction(self):
        if self.test_tx_hash is None:
            nonce = self.web3.zksync.get_transaction_count(
                self.account.address, ZkBlockParams.COMMITTED.value
            )
            gas_price = self.web3.zksync.gas_price
            tx_func_call = TxFunctionCall(
                chain_id=self.chain_id,
                nonce=nonce,
                from_=self.account.address,
                to=self.account.address,
                value=Web3.to_wei(0.01, "ether"),
                data=HexStr("0x"),
                gas_limit=0,  # UNKNOWN AT THIS STATE
                gas_price=gas_price,
                max_priority_fee_per_gas=100000000,
            )
            estimate_gas = self.web3.zksync.eth_estimate_gas(tx_func_call.tx)

            tx_712 = tx_func_call.tx712(estimate_gas)
            singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
            msg = tx_712.encode(singed_message)
            self.test_tx_hash = self.web3.zksync.send_raw_transaction(msg)
            self.web3.zksync.wait_for_transaction_receipt(self.test_tx_hash)
        tx = self.web3.zksync.get_transaction(self.test_tx_hash)
        self.assertEqual(tx["from"], self.account.address)

    # @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_transfer_native(self):
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, ZkBlockParams.COMMITTED.value
        )
        gas_price = self.web3.zksync.gas_price
        func_call = TxFunctionCall(
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            to=self.account.address,
            gas_limit=0,
            gas_price=gas_price,
        )

        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        self.assertGreater(
            estimate_gas,
            0,
            "test_estimate_gas_transfer_native, estimate_gas must be greater 0",
        )

    # @skip("Integration test, used for develop purposes only")
    def test_estimate_fee_transfer_native(self):
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, ZkBlockParams.COMMITTED.value
        )
        gas_price = self.web3.zksync.gas_price

        func_call = TxFunctionCall(
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            to=self.account.address,
            gas_limit=0,
            gas_price=gas_price,
        )
        estimated_fee = self.web3.zksync.zks_estimate_fee(func_call.tx)

    # @skip("Integration test, used for develop purposes only")
    def test_transfer_native_to_self(self):
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, ZkBlockParams.COMMITTED.value
        )
        gas_price = self.web3.zksync.gas_price
        tx_func_call = TxFunctionCall(
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            to=self.account.address,
            value=Web3.to_wei(0.01, "ether"),
            data=HexStr("0x"),
            gas_limit=0,  # UNKNOWN AT THIS STATE
            gas_price=gas_price,
            max_priority_fee_per_gas=100000000,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx_func_call.tx)

        tx_712 = tx_func_call.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertEqual(1, tx_receipt["status"])

    def deploy_erc20_token_builder(self):
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, ZkBlockParams.COMMITTED.value
        )
        counter_contract = ContractEncoder.from_json(
            self.web3, contract_path("SomeERC20.json")
        )
        random_salt = generate_random_salt()
        gas_price = self.web3.zksync.gas_price
        create_contract = TxCreateContract(
            web3=self.web3,
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            gas_limit=0,  # UNKNOWN AT THIS STATE
            gas_price=gas_price,
            bytecode=counter_contract.bytecode,
            salt=random_salt,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)
        tx_712 = create_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertEqual(1, tx_receipt["status"])
        contract_address = tx_receipt["contractAddress"]
        if self.some_erc20_address is None:
            self.some_erc20_address = contract_address

    def mint_some_erc20(self, amount: int):
        some_erc20_encoder = ContractEncoder.from_json(
            self.web3, contract_path("SomeERC20.json")
        )
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.LATEST.value
        )
        gas_price = self.web3.zksync.gas_price

        args = (self.account.address, self.ERC20_Token.to_int(amount))
        call_data = some_erc20_encoder.encode_method(fn_name="mint", args=args)
        func_call = TxFunctionCall(
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            to=self.some_erc20_address,
            data=call_data,
            gas_limit=0,  # UNKNOWN AT THIS STATE,
            gas_price=gas_price,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)

        tx_712 = func_call.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertEqual(1, tx_receipt["status"])

    # @skip("Integration test, used for develop purposes only")
    def test_estimate_gas_deploy_contract(self):
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Counter.json")
        counter_contract = ContractEncoder.from_json(
            self.web3, path.resolve(), JsonConfiguration.STANDARD
        )
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.PENDING.value
        )
        gas_price = self.web3.zksync.gas_price
        create2_contract = TxCreate2Contract(
            web3=self.web3,
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            gas_limit=0,
            gas_price=gas_price,
            bytecode=counter_contract.bytecode,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)
        self.assertGreater(
            estimate_gas,
            0,
            "test_estimate_gas_deploy_contract, estimate_gas must be greater 0",
        )

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_create(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.PENDING.value
        )
        nonce_holder = self.web3.zksync.contract(
            address=ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value,
            abi=nonce_holder_abi_default(),
        )
        deployment_nonce = nonce_holder.functions.getDeploymentNonce(
            self.account.address
        ).call({"from": self.account.address})
        deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = deployer.compute_l2_create_address(
            self.account.address, deployment_nonce
        )
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Counter.json")
        counter_contract = ContractEncoder.from_json(
            self.web3, path.resolve(), JsonConfiguration.STANDARD
        )

        gas_price = self.web3.zksync.gas_price
        create_contract = TxCreateContract(
            web3=self.web3,
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            gas_limit=0,  # UNKNOWN AT THIS STATE
            gas_price=gas_price,
            bytecode=counter_contract.bytecode,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)
        tx_712 = create_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertEqual(1, tx_receipt["status"])
        contract_address = tx_receipt["contractAddress"]
        self.counter_address = contract_address

        self.assertEqual(precomputed_address.lower(), contract_address.lower())

        value = counter_contract.contract.functions.get().call(
            {"from": self.account.address, "to": contract_address}
        )
        self.assertEqual(0, value)

    @skip("web3py 6.0.0 does not provide protocol version")
    def test_protocol_version(self):
        version = self.web3.zksync.protocol_version
        self.assertEqual(version, "zks/1")

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_constructor_create(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.PENDING.value
        )
        gas_price = self.web3.zksync.gas_price

        nonce_holder = self.web3.zksync.contract(
            address=ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value,
            abi=nonce_holder_abi_default(),
        )
        deployment_nonce = nonce_holder.functions.getDeploymentNonce(
            self.account.address
        ).call({"from": self.account.address})
        deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = deployer.compute_l2_create_address(
            self.account.address, deployment_nonce
        )

        directory = Path(__file__).parent
        path = directory / Path("../contracts/SimpleConstructor.json")
        constructor_encoder = ContractEncoder.from_json(
            self.web3, path.resolve(), JsonConfiguration.STANDARD
        )
        a = 2
        b = 3
        encoded_ctor = constructor_encoder.encode_constructor(
            a=a, b=b, shouldRevert=False
        )

        create_contract = TxCreateContract(
            web3=self.web3,
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            gas_limit=0,  # UNKNOWN AT THIS STATE,
            gas_price=gas_price,
            bytecode=constructor_encoder.bytecode,
            call_data=encoded_ctor,
        )

        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)

        tx_712 = create_contract.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertEqual(1, tx_receipt["status"])

        contract_address = tx_receipt["contractAddress"]
        # INFO: does not work, contract_address is None
        self.assertEqual(precomputed_address.lower(), contract_address.lower())
        contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=constructor_encoder.abi,
        )

        value = contract.functions.get().call(
            {"from": self.account.address, "to": contract_address}
        )
        self.assertEqual(a * b, value)

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_create2(self):
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.PENDING.value
        )
        gas_price = self.web3.zksync.gas_price
        deployer = PrecomputeContractDeployer(self.web3)

        directory = Path(__file__).parent
        path = directory / Path("../contracts/Counter.json")
        counter_contract_encoder = ContractEncoder.from_json(
            self.web3, path.resolve(), JsonConfiguration.STANDARD
        )
        precomputed_address = deployer.compute_l2_create2_address(
            sender=self.account.address,
            bytecode=counter_contract_encoder.bytecode,
            constructor=b"",
            salt=random_salt,
        )
        create2_contract = TxCreate2Contract(
            web3=self.web3,
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            gas_limit=0,
            gas_price=gas_price,
            bytecode=counter_contract_encoder.bytecode,
            salt=random_salt,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)

        tx_712 = create2_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=1.0
        )

        self.assertEqual(1, tx_receipt["status"])

        contract_address = tx_receipt["contractAddress"]
        self.counter_address = contract_address

        self.assertEqual(precomputed_address.lower(), contract_address.lower())

        value = counter_contract_encoder.contract.functions.get().call(
            {"from": self.account.address, "to": contract_address}
        )
        self.assertEqual(0, value)

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_deps_create(self):
        random_salt = generate_random_salt()
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Import.json")
        import_contract = ContractEncoder.from_json(
            self.web3, path.resolve(), JsonConfiguration.STANDARD
        )
        directory = Path(__file__).parent
        foo_path = directory / Path("../contracts/Foo.json")
        import_dependency_contract = ContractEncoder.from_json(
            self.web3, foo_path.resolve(), JsonConfiguration.STANDARD
        )
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.PENDING.value
        )
        gas_price = self.web3.zksync.gas_price
        nonce_holder = self.web3.zksync.contract(
            address=ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value,
            abi=nonce_holder_abi_default(),
        )
        deployment_nonce = nonce_holder.functions.getDeploymentNonce(
            self.account.address
        ).call({"from": self.account.address})
        contract_deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = contract_deployer.compute_l2_create_address(
            self.account.address, deployment_nonce
        )

        create_contract = TxCreateContract(
            web3=self.web3,
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            gas_limit=0,
            gas_price=gas_price,
            bytecode=import_contract.bytecode,
            deps=[import_dependency_contract.bytecode],
        )

        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)

        tx_712 = create_contract.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertEqual(1, tx_receipt["status"])

        contract_address = contract_deployer.extract_contract_address(tx_receipt)
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

    # @skip("Integration test, used for develop purposes only")
    def test_deploy_contract_with_deps_create2(self):
        random_salt = generate_random_salt()
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Import.json")
        import_contract = ContractEncoder.from_json(
            self.web3, path.resolve(), JsonConfiguration.STANDARD
        )
        directory = Path(__file__).parent
        foo_path = directory / Path("../contracts/Foo.json")
        import_dependency_contract = ContractEncoder.from_json(
            self.web3, foo_path.resolve(), JsonConfiguration.STANDARD
        )
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.PENDING.value
        )
        gas_price = self.web3.zksync.gas_price

        contract_deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = contract_deployer.compute_l2_create2_address(
            self.account.address,
            bytecode=import_contract.bytecode,
            constructor=b"",
            salt=random_salt,
        )
        create2_contract = TxCreate2Contract(
            web3=self.web3,
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            gas_limit=0,
            gas_price=gas_price,
            bytecode=import_contract.bytecode,
            deps=[import_dependency_contract.bytecode],
            salt=random_salt,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)

        tx_712 = create2_contract.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertEqual(1, tx_receipt["status"])
        contract_address = contract_deployer.extract_contract_address(tx_receipt)
        self.assertEqual(precomputed_address.lower(), contract_address.lower())

    # @skip("Integration test, used for develop purposes only")
    def test_execute_contract(self):
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Counter.json")
        counter_contract = ContractEncoder.from_json(
            self.web3, path.resolve(), JsonConfiguration.STANDARD
        )
        if self.counter_address is None:
            random_salt = generate_random_salt()
            nonce = self.web3.zksync.get_transaction_count(
                self.account.address, EthBlockParams.PENDING.value
            )
            gas_price = self.web3.zksync.gas_price
            create_contract = TxCreateContract(
                web3=self.web3,
                chain_id=self.chain_id,
                nonce=nonce,
                from_=self.account.address,
                gas_limit=0,  # UNKNOWN AT THIS STATE
                gas_price=gas_price,
                bytecode=counter_contract.bytecode,
            )
            estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)
            tx_712 = create_contract.tx712(estimate_gas)
            singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
            msg = tx_712.encode(singed_message)
            tx_hash = self.web3.zksync.send_raw_transaction(msg)
            tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
                tx_hash, timeout=240, poll_latency=0.5
            )
            self.assertEqual(1, tx_receipt["status"])
            contract_address = tx_receipt["contractAddress"]
            self.counter_address = contract_address

        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.LATEST.value
        )
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
        func_call = TxFunctionCall(
            chain_id=self.chain_id,
            nonce=nonce,
            from_=self.account.address,
            to=self.counter_address,
            data=call_data,
            gas_limit=0,  # UNKNOWN AT THIS STATE,
            gas_price=gas_price,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)

        tx_712 = func_call.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertEqual(1, tx_receipt["status"])

        eth_ret2 = self.web3.zksync.call(eth_tx, EthBlockParams.LATEST.value)
        updated_result = int.from_bytes(eth_ret2, "big", signed=True)
        self.assertEqual(result + 1, updated_result)

    # @skip
    def test_contract_factory(self):
        increment_value = 10
        salt = generate_random_salt()
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Counter.json")
        deployer = LegacyContractFactory.from_json(
            zksync=self.web3,
            compiled_contract=path.resolve(),
            account=self.account,
            signer=self.signer,
        )
        contract = deployer.deploy()
        value = contract.functions.get().call({"from": self.account.address})

        gas_price = self.web3.zksync.gas_price
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.LATEST.value
        )
        tx = contract.functions.increment(increment_value).build_transaction(
            {
                "nonce": nonce,
                "from": self.account.address,
                # INFO: this fields can't be got automatically because internally
                #      web3 py uses web3.eth provider with specific lambdas for getting them
                "maxPriorityFeePerGas": 1000000,
                "maxFeePerGas": gas_price,
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.zksync.send_raw_transaction(signed.rawTransaction)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(1, tx_receipt["status"])

        value = contract.functions.get().call(
            {
                "from": self.account.address,
            }
        )
        self.assertEqual(increment_value, value)

    # @skip("Integration test, used for develop purposes only")
    def test_get_all_account_balances(self):
        balances = self.web3.zksync.zks_get_all_account_balances(self.account.address)


    # @skip("Integration test, used for develop purposes only")
    def test_get_l1_chain_id(self):
        self.assertIsInstance(self.web3.zksync.zks_l1_chain_id(), int)

    # @skip("Integration test, used for develop purposes only")
    def test_get_bridge_addresses(self):
        result = self.web3.zksync.zks_get_bridge_contracts()
        self.assertIsNotNone(result)

    def test_get_account_info(self):
        TESTNET_PAYMASTER = "0x0f9acdb01827403765458b4685de6d9007580d15"
        result = self.web3.zksync.get_contract_account_info(TESTNET_PAYMASTER)

        self.assertIsNotNone(result)

    def test_get_l1_token_address(self):
        result = self.web3.zksync.l1_token_address(ADDRESS_DEFAULT)
        self.assertEqual(result, ADDRESS_DEFAULT)

    def test_get_l2_token_address(self):
        result = self.web3.zksync.l2_token_address(ADDRESS_DEFAULT)
        self.assertEqual(result, L2_BASE_TOKEN_ADDRESS)

    def test_get_bridgehub_contract(self):
        result = self.web3.zksync.zks_get_bridgehub_contract_address()
        self.assertIsNotNone(result)

    def test_zks_get_base_token_contract_address(self):
        result = self.web3.zksync.zks_get_base_token_contract_address()
        self.assertIsNotNone(result)
