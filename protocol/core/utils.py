import sys
from hashlib import sha256
from typing import Union

from eth_typing import HexStr, Address, ChecksumAddress


def int_to_bytes(x: int) -> bytes:
    return x.to_bytes((x.bit_length() + 7) // 8, byteorder=sys.byteorder)


def get_data(data: Union[bytes, HexStr]) -> bytes:
    if isinstance(data, bytes):
        return data
    if data.startswith("0x"):
        data = data[2:]
    return bytes.fromhex(data)


# def _get_v(signature) -> bytes:
#     v_bytes = bytes()
#     # TODO: getV[0] is big endian or little , and what is the bytes amount??
#     if signature.v != 0:
#         v_bytes = int_to_bytes(signature.v)
#     return v_bytes


def encode_address(addr: Union[Address, ChecksumAddress, str]) -> bytes:
    if len(addr) == 0:
        return bytes()
    if isinstance(addr, bytes):
        return addr
    if addr.startswith("0x"):
        addr = addr[2:]
    return bytes.fromhex(addr)


def hash_byte_code(bytecode: bytes) -> bytes:
    bytecode_hash = bytes.fromhex(sha256(bytecode).hexdigest())
    bytecode_size = int(len(bytecode_hash) / 32)
    if bytecode_size > 2 ** 16:
        raise OverflowError("hash_byte_code, bytecode length must be less than 2^16")
    ret = bytecode_size.to_bytes(2, byteorder='big') + bytecode_hash[2:]
    return ret


def pad_front_bytes(bs: bytes, needed_length: int):
    padded = b'\0' * (needed_length - len(bs)) + bs
    return padded
