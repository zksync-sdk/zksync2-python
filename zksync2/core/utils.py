import sys
from enum import IntEnum
from hashlib import sha256
from typing import Union

from eth_typing import HexStr, Address, ChecksumAddress
from eth_utils import remove_0x_prefix
from web3 import Web3

from zksync2.core.types import ADDRESS_DEFAULT, L2_ETH_TOKEN_ADDRESS
from zksync2.manage_contracts.erc20_contract import get_erc20_abi
from zksync2.manage_contracts.l2_bridge import get_l2_bridge_abi

L1_TO_L2_ALIAS_OFFSET = HexStr('0x1111000000000000000000000000000000001111')
ADDRESS_MODULO = pow(2,160)


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


class RecommendedGasLimit(IntEnum):
    DEPOSIT = 10000000
    EXECUTE = 620000
    ERC20_APPROVE = 50000


def apply_l1_to_l2_alias(address: ChecksumAddress) -> ChecksumAddress:
    return  Web3.to_checksum_address(hex((int(address, 16) + int(L1_TO_L2_ALIAS_OFFSET,16)) % ADDRESS_MODULO))


def undo_l1_to_l2_alias(address: ChecksumAddress) -> ChecksumAddress:
    result = int(address, 16) - int(L1_TO_L2_ALIAS_OFFSET, 16)
    if result < 0:
        result += ADDRESS_MODULO
    return Web3.to_checksum_address(hex(result))


def get_erc20_default_bridge_data(l1_token_address: ChecksumAddress, provider: Web3) -> bytes:
    token_contract = provider.eth.contract(l1_token_address, abi=get_erc20_abi())

    name = token_contract.functions.name().call()
    symbol = token_contract.functions.symbol().call()
    decimals = token_contract.functions.decimals().call()

    name_encoded = provider.eth.codec.encode(["string"], [name])
    symbol_encoded = provider.eth.codec.encode(["string"], [symbol])
    decimals_encoded = provider.eth.codec.encode(["uint256"], [decimals])

    return provider.eth.codec.encode(["bytes", "bytes", "bytes"], [name_encoded, symbol_encoded, decimals_encoded])


# returns the calldata that will be sent by an L1 ERC20 bridge to its L2 counterpart during bridging of a token.
def get_erc20_bridge_calldata(l1_token_address: ChecksumAddress,
                              l1_sender: ChecksumAddress,
                              l2_receiver: ChecksumAddress,
                              amount: int,
                              bridge_data: bytes) -> bytes:
    l2_bridge = Web3.eth.contract(l1_token_address, abi=get_l2_bridge_abi())
    return l2_bridge.encodeABI("finalizeDeposit", l1_sender, l2_receiver, l1_token_address, amount, bridge_data)
