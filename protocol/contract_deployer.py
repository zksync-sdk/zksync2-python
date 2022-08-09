from web3 import Web3
from eth_utils.crypto import keccak_256
from pathlib import Path
from typing import Optional
import json

icontract_deployer_abi_cache = None
icontract_deployer_abi_default_path = Path('./contract_abi/IContractDeployer.json')


def _icontract_deployer_abi_default():
    global icontract_deployer_abi_cache

    if icontract_deployer_abi_cache is None:
        with icontract_deployer_abi_default_path.open(mode='r') as json_file:
            data = json.load(json_file)
            erc_20_abi_cache = data['abi']
    return erc_20_abi_cache


class ContractDeployer:
    DEFAULT_SALT = b'\0' * 32
    CREATE2_FUNC = "create2"
    MAX_BYTE_CODE_LENGTH = 2 ** 16

    def __init__(self, abi: Optional[dict] = None):
        if abi is None:
            abi = _icontract_deployer_abi_default()

        self.contract_deployer = Web3.eth.contract(address=None, abi=abi)

    def _hash_byte_code(self, bytecode: bytes) -> bytes:
        bytecode_len = int(len(bytecode) / 32)
        if bytecode_len > self.MAX_BYTE_CODE_LENGTH:
            raise OverflowError("ContractDeployer._hash_byte_code, bytecode length must be less than 2^16")
        byte_code_hash = keccak_256(bytecode)
        ret = bytecode_len.to_bytes(2, byteorder='big') + byte_code_hash
        return ret

    def encode_data(self, bytecode: bytes, salt: bytes = None) -> bytes:
        if salt is None:
            salt = self.DEFAULT_SALT

        if len(salt) != 32:
            raise OverflowError("Salt data must be 32 length")

        bytecode = self._hash_byte_code(bytecode)
        args = [
            salt,
            bytecode,
            0,
            b''
        ]
        encoded_function = self.contract_deployer.encodeABI(fn_name=self.CREATE2_FUNC, args=args)
        return encoded_function
