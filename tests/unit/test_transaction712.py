from unittest import TestCase

from eip712_structs import make_domain
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from eth_utils.crypto import keccak
from web3 import Web3
from web3.types import Nonce

from tests.contracts.utils import contract_path
from test_config import LOCAL_ENV
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.module.request_types import EIP712Meta
from zksync2.transaction.transaction712 import Transaction712
from zksync2.transaction.transaction_builders import TxCreateContract

PRIVATE_KEY2 = bytes.fromhex("fd1f96220fa3a40c46d65f81d61dd90af600746fd47e5c82673da937a48b38ef")


class Transaction712Tests(TestCase):
    NONCE = Nonce(42)
    CHAIN_ID = 42
    GAS_LIMIT = 54321
    SENDER = HexStr("0x1234512345123451234512345123451234512345")
    RECEIVER = HexStr("0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC")

    TRANSACTION_SIGNATURE = "Transaction(uint256 txType,uint256 from,uint256 to,uint256 gasLimit,uint256 " \
                            "gasPerPubdataByteLimit,uint256 maxFeePerGas,uint256 maxPriorityFeePerGas," \
                            "uint256 paymaster,uint256 nonce,uint256 value,bytes data,bytes32[] factoryDeps," \
                            "bytes paymasterInput)"

    EXPECTED_ENCODED_VALUE = '0x1e40bcee418db11047ffefb27b304f8ec1b5d644c35c56878f5cc12988b3162d'
    EXPECTED_ENCODED_BYTES = "0x7519adb6e67031ee048d921120687e4fbdf83961bcf43756f349d689eed2b80c"

    def setUp(self) -> None:
        # self.web3 = Web3(EthereumTesterProvider(PyEVMBackend()))
        self.env = LOCAL_ENV
        self.web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        self.account: LocalAccount = Account.from_key(PRIVATE_KEY2)
        self.counter_contract_encoder = ContractEncoder.from_json(self.web3, contract_path("Counter.json"))
        self.tx712 = Transaction712(chain_id=self.CHAIN_ID,
                                    nonce=self.NONCE,
                                    gas_limit=self.GAS_LIMIT,
                                    to=self.RECEIVER,
                                    value=0,
                                    data=self.counter_contract_encoder.encode_method(fn_name="increment", args=[42]),
                                    maxPriorityFeePerGas=0,
                                    maxFeePerGas=0,
                                    from_=self.SENDER,
                                    meta=EIP712Meta(0))

    def test_deploy_contract_tx712(self):
        tx = TxCreateContract(web3=self.web3,
                              chain_id=280,
                              nonce=0,
                              from_=self.account.address.lower(),
                              gas_limit=0,  # UNKNOWN AT THIS STATE
                              gas_price=250000000,
                              bytecode=self.counter_contract_encoder.bytecode)
        tx_712 = tx.tx712(9910372)
        msg = tx_712.to_eip712_struct().hash_struct()
        self.assertEqual("b65d7e33b4d31aa931d044aff74ad6780374acd5bcbd192b1b0210c40664ccb2",
                         msg.hex())

    def test_encode_to_eip712_type_string(self):
        eip712_struct = self.tx712.to_eip712_struct()
        ret = eip712_struct.encode_type()
        self.assertEqual(self.TRANSACTION_SIGNATURE, ret)

    def test_serialize_to_eip712_encoded_value(self):
        eip712_struct = self.tx712.to_eip712_struct()
        encoded_value = eip712_struct.hash_struct()
        result = "0x" + encoded_value.hex()
        self.assertEqual(self.EXPECTED_ENCODED_VALUE, result)

    def test_serialize_to_eip712_message(self):
        domain = make_domain(name="zkSync", version="2", chainId=self.CHAIN_ID)
        eip712_struct = self.tx712.to_eip712_struct()

        result_bytes = eip712_struct.signable_bytes(domain)
        msg = keccak(result_bytes)
        result = "0x" + msg.hex()
        self.assertEqual(self.EXPECTED_ENCODED_BYTES, result)
