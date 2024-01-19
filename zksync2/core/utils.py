import sys
from enum import IntEnum
from hashlib import sha256
from typing import Union

from eth_abi import encode
from eth_typing import HexStr, Address, ChecksumAddress
from eth_utils import remove_0x_prefix, add_0x_prefix
from hexbytes import HexBytes
from web3 import Web3

ADDRESS_MODULO = pow(2, 160)
L1_TO_L2_ALIAS_OFFSET = "0x1111000000000000000000000000000000001111"

ADDRESS_DEFAULT = HexStr("0x" + "0" * 40)
L2_ETH_TOKEN_ADDRESS = HexStr("0x000000000000000000000000000000000000800a")
BOOTLOADER_FORMAL_ADDRESS = HexStr("0x0000000000000000000000000000000000008001")

DEPOSIT_GAS_PER_PUBDATA_LIMIT = 800
MAX_PRIORITY_FEE_PER_GAS = 100_000_000


def int_to_bytes(x: int) -> bytes:
    return x.to_bytes((x.bit_length() + 7) // 8, byteorder=sys.byteorder)


def to_bytes(data: Union[bytes, HexStr]) -> bytes:
    if isinstance(data, bytes):
        return data
    return bytes.fromhex(remove_0x_prefix(data))


def is_eth(address: HexStr) -> bool:
    return address.lower() == ADDRESS_DEFAULT or address.lower() == L2_ETH_TOKEN_ADDRESS


def encode_address(addr: Union[Address, ChecksumAddress, str]) -> bytes:
    if len(addr) == 0:
        return bytes()
    if isinstance(addr, bytes):
        return addr
    return bytes.fromhex(remove_0x_prefix(addr))


def hash_byte_code(bytecode: bytes) -> bytes:
    bytecode_len = len(bytecode)
    bytecode_size = int(bytecode_len / 32)
    if bytecode_len % 32 != 0:
        raise RuntimeError("Bytecode length in 32-byte words must be odd")
    if bytecode_size > 2**16:
        raise OverflowError("hash_byte_code, bytecode length must be less than 2^16")
    bytecode_hash = sha256(bytecode).digest()
    encoded_len = bytecode_size.to_bytes(2, byteorder="big")
    ret = b"\x01\00" + encoded_len + bytecode_hash[4:]
    return ret


def pad_front_bytes(bs: bytes, needed_length: int):
    padded = b"\0" * (needed_length - len(bs)) + bs
    return padded


def get_custom_bridge_data(token_contract) -> bytes:
    name = token_contract.functions.name().call()
    symbol = token_contract.functions.symbol().call()
    decimals = token_contract.functions.decimals().call()
    name_encoded = encode(["string"], [name])
    symbol_encoded = encode(["string"], [symbol])
    decimals_encoded = encode(["uint256"], [decimals])

    return encode(
        ["bytes", "bytes", "bytes"], [name_encoded, symbol_encoded, decimals_encoded]
    )


def apply_l1_to_l2_alias(address: HexStr):
    value = (int(L1_TO_L2_ALIAS_OFFSET, 16) + int(address, 16)) % ADDRESS_MODULO
    hex_result = remove_0x_prefix(Web3.to_hex(value))
    result = hex_result.rjust(40, "0")
    return add_0x_prefix(result)


def undo_l1_to_l2_alias(address: HexStr):
    result = int(address, 16) - int(L1_TO_L2_ALIAS_OFFSET, 16)
    if result < 0:
        result += ADDRESS_MODULO

    return Web3.to_hex(result)


class RequestExecuteTransaction:
    pass


class RecommendedGasLimit(IntEnum):
    DEPOSIT = 10000000
    EXECUTE = 620000
    ERC20_APPROVE = 50000
    DEPOSIT_GAS_PER_PUBDATA_LIMIT = 800
    L1_RECOMMENDED_ETH_DEPOSIT_GAS_LIMIT = 200000
    L1_RECOMMENDED_MIN_ERC_20_DEPOSIT_GAS_LIMIT = 400000
