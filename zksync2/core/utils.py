import sys
from hashlib import sha256
from typing import Union

from eth_typing import HexStr, Address, ChecksumAddress
from eth_utils import remove_0x_prefix


def int_to_bytes(x: int) -> bytes:
    return x.to_bytes((x.bit_length() + 7) // 8, byteorder=sys.byteorder)


def to_bytes(data: Union[bytes, HexStr]) -> bytes:
    if isinstance(data, bytes):
        return data
    return bytes.fromhex(remove_0x_prefix(data))


def encode_address(addr: Union[Address, ChecksumAddress, str]) -> bytes:
    if len(addr) == 0:
        return bytes()
    if isinstance(addr, bytes):
        return addr
    return bytes.fromhex(remove_0x_prefix(addr))


def hash_byte_code(bytecode: bytes) -> bytes:
    bytecode_hash = bytes.fromhex(sha256(bytecode).hexdigest())
    bytecode_size = int(len(bytecode) / 32)
    if bytecode_size > 2 ** 16:
        raise OverflowError("hash_byte_code, bytecode length must be less than 2^16")
    ret = bytecode_size.to_bytes(2, byteorder='big') + bytecode_hash[2:]
    return ret


def pad_front_bytes(bs: bytes, needed_length: int):
    padded = b'\0' * (needed_length - len(bs)) + bs
    return padded
