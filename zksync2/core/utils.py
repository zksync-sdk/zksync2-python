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
    bytecode_len = len(bytecode)
    bytecode_size = int(bytecode_len / 32)
    if bytecode_len % 32 != 0:
        raise RuntimeError('Bytecode length in 32-byte words must be odd')
    if bytecode_size > 2 ** 16:
        raise OverflowError("hash_byte_code, bytecode length must be less than 2^16")
    bytecode_hash = sha256(bytecode).digest()
    encoded_len = bytecode_size.to_bytes(2, byteorder='big')
    ret = b'\x01\00' + encoded_len + bytecode_hash[4:]
    return ret


def pad_front_bytes(bs: bytes, needed_length: int):
    padded = b'\0' * (needed_length - len(bs)) + bs
    return padded
