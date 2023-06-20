import importlib.resources as pkg_resources
import json
from typing import Optional

from eth_typing import HexStr
from eth_utils.crypto import keccak
from web3 import Web3
from web3.logs import DISCARD
from web3.types import Nonce, TxReceipt

from zksync2.core.types import AccountAbstractionVersion
from zksync2.core.utils import pad_front_bytes, to_bytes, int_to_bytes, hash_byte_code
from zksync2.manage_contracts import contract_abi
from zksync2.manage_contracts.contract_encoder_base import BaseContractEncoder

icontract_deployer_abi_cache = None


def _icontract_deployer_abi_default():
    global icontract_deployer_abi_cache

    if icontract_deployer_abi_cache is None:
        with pkg_resources.path(contract_abi, "ContractDeployer.json") as p:
            with p.open(mode='r') as json_file:
                data = json.load(json_file)
                icontract_deployer_abi_cache = data["abi"]
    return icontract_deployer_abi_cache


class PrecomputeContractDeployer:
    DEFAULT_SALT = b'\0' * 32
    CREATE_FUNC = "create"
    CREATE2_FUNC = "create2"
    CREATE_ACCOUNT_FUNC = "createAccount"
    CREATE2_ACCOUNT_FUNC = "create2Account"
    MAX_BYTE_CODE_LENGTH = 2 ** 16
    EMPTY_BYTES = b''

    CREATE_PREFIX = keccak(text="zksyncCreate")
    CREATE2_PREFIX = keccak(text="zksyncCreate2")

    def __init__(self, web3: Web3, abi: Optional[dict] = None):
        self.web3 = web3
        if abi is None:
            abi = _icontract_deployer_abi_default()
        self.contract_encoder = BaseContractEncoder(self.web3, abi)

    def encode_create2(self, bytecode: bytes,
                       call_data: Optional[bytes] = None,
                       salt: Optional[bytes] = None) -> HexStr:

        if salt is None:
            salt = self.DEFAULT_SALT
        if call_data is None:
            call_data = self.EMPTY_BYTES

        if len(salt) != 32:
            raise OverflowError("Salt data must be 32 length")

        bytecode_hash = hash_byte_code(bytecode)
        args = salt, bytecode_hash, call_data

        return self.contract_encoder.encode_method(fn_name=self.CREATE2_FUNC, args=args)

    def encode_create(self, bytecode: bytes, call_data: Optional[bytes] = None) -> HexStr:
        if call_data is None:
            call_data = self.EMPTY_BYTES

        bytecode_hash = hash_byte_code(bytecode)
        args = self.DEFAULT_SALT, bytecode_hash, call_data

        return self.contract_encoder.encode_method(fn_name=self.CREATE_FUNC, args=args)

    def encode_create2_account(self, bytecode: bytes,
                               call_data: Optional[bytes] = None,
                               salt: Optional[bytes] = None,
                               version: AccountAbstractionVersion = AccountAbstractionVersion.VERSION_1
                               ) -> HexStr:
        if salt is None:
            salt = self.DEFAULT_SALT
        if call_data is None:
            call_data = self.EMPTY_BYTES

        if len(salt) != 32:
            raise OverflowError("Salt data must be 32 length")

        bytecode_hash = hash_byte_code(bytecode)
        args = salt, bytecode_hash, call_data, version.value

        return self.contract_encoder.encode_method(fn_name=self.CREATE2_ACCOUNT_FUNC, args=args)

    def encode_create_account(self, bytecode: bytes,
                              call_data: Optional[bytes] = None,
                              version: AccountAbstractionVersion = AccountAbstractionVersion.VERSION_1
                              ) -> HexStr:
        if call_data is None:
            call_data = self.EMPTY_BYTES

        bytecode_hash = hash_byte_code(bytecode)
        args = self.DEFAULT_SALT, bytecode_hash, call_data, version.value

        return self.contract_encoder.encode_method(fn_name=self.CREATE_ACCOUNT_FUNC, args=args)

    def compute_l2_create_address(self, sender: HexStr, nonce: Nonce) -> HexStr:
        sender_bytes = to_bytes(sender)
        sender_bytes = pad_front_bytes(sender_bytes, 32)
        nonce = int_to_bytes(nonce)
        nonce_bytes = pad_front_bytes(nonce, 32)
        result = self.CREATE_PREFIX + sender_bytes + nonce_bytes
        sha_result = keccak(result)
        address = sha_result[12:]
        address = "0x" + address.hex()
        return HexStr(Web3.to_checksum_address(address))

    def compute_l2_create2_address(self,
                                   sender: HexStr,
                                   bytecode: bytes,
                                   constructor: bytes,
                                   salt: bytes) -> HexStr:
        if len(salt) != 32:
            raise OverflowError("Salt data must be 32 length")

        sender_bytes = to_bytes(sender)
        sender_bytes = pad_front_bytes(sender_bytes, 32)
        bytecode_hash = hash_byte_code(bytecode)
        ctor_hash = keccak(constructor)
        result = self.CREATE2_PREFIX + sender_bytes + salt + bytecode_hash + ctor_hash
        sha_result = keccak(result)
        address = sha_result[12:]
        address = "0x" + address.hex()
        return HexStr(Web3.to_checksum_address(address))

    def extract_contract_address(self, receipt: TxReceipt) -> HexStr:
        result = self.contract_encoder.contract.events.ContractDeployed().process_receipt(receipt, errors=DISCARD)
        entry = result[1]["args"]
        addr = entry["contractAddress"]
        return addr
