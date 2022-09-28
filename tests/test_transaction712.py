from unittest import TestCase
from eth_utils.crypto import keccak_256
from eip712_structs import make_domain
from eth_tester import PyEVMBackend
from eth_typing import HexStr
from web3 import Web3, EthereumTesterProvider
from web3.types import Nonce

from zksync2.module.request_types import EIP712Meta
from zksync2.transaction.transaction712 import Transaction712
from tests.contracts.counter_contract_utils import CounterContractEncoder


class TestTransaction712(TestCase):

    NONCE = Nonce(42)
    CHAIN_ID = 42
    GAS_LIMIT = 54321
    SENDER = HexStr("0x1234512345123451234512345123451234512345")
    RECEIVER = HexStr("0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC")

    EXPECTED_TYPE_STRING = "Transaction(uint256 txType,uint256 from,uint256 to,uint256 " \
                           "ergsLimit,uint256 ergsPerPubdataByteLimit,uint256 maxFeePerErg," \
                           "uint256 maxPriorityFeePerErg,uint256 paymaster,uint256 nonce," \
                           "uint256 value,bytes data,bytes32[] factoryDeps,bytes paymasterInput)"

    EXPECTED_ENCODED_VALUE = "0x2360af215549f2e44413f5a6eb25ecf40590c231e24a70b23a942f995814dc77"
    EXPECTED_ENCODED_BYTES = "0x2506074540188226a81a8dc006ab311c06b680232d39699d348e8ec83c81388b"

    def setUp(self) -> None:

        self.web3 = Web3(EthereumTesterProvider(PyEVMBackend()))
        counter_contract = CounterContractEncoder(self.web3)
        self.tx712 = Transaction712(chain_id=self.CHAIN_ID,
                                    nonce=self.NONCE,
                                    gas_limit=self.GAS_LIMIT,
                                    to=self.RECEIVER,
                                    value=0,
                                    data=counter_contract.encode_method(fn_name="increment", args=[42]),
                                    maxPriorityFeePerGas=0,
                                    maxFeePerGas=0,
                                    from_=self.SENDER,
                                    meta=EIP712Meta(0))

    def test_encode_to_eip712_type_string(self):
        eip712_struct = self.tx712.to_eip712_struct()
        ret = eip712_struct.encode_type()
        self.assertEqual(self.EXPECTED_TYPE_STRING, ret)

    def test_serialize_to_eip712_encoded_value(self):
        eip712_struct = self.tx712.to_eip712_struct()
        encoded_value = eip712_struct.hash_struct()
        result = "0x" + encoded_value.hex()
        self.assertEqual(self.EXPECTED_ENCODED_VALUE, result)

    def test_serialize_to_eip712_message(self):
        domain = make_domain(name="zkSync", version="2", chainId=self.CHAIN_ID)
        eip712_struct = self.tx712.to_eip712_struct()

        result_bytes = eip712_struct.signable_bytes(domain)
        msg = keccak_256(result_bytes)
        result = "0x" + msg.hex()
        self.assertEqual(self.EXPECTED_ENCODED_BYTES, result)
