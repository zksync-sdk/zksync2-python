import sys
from enum import IntEnum
from hashlib import sha256
from typing import Union

from eth_abi import encode
from eth_typing import HexStr, Address, ChecksumAddress
from eth_utils import remove_0x_prefix
from hexbytes import HexBytes
from web3 import Web3

ADDRESS_MODULO = pow(2, 160)
L1_TO_L2_ALIAS_OFFSET = "0x1111000000000000000000000000000000001111"

ADDRESS_DEFAULT = HexStr("0x" + "0" * 40)
L2_ETH_TOKEN_ADDRESS = HexStr('0x000000000000000000000000000000000000800a')
BOOTLOADER_FORMAL_ADDRESS = HexStr("0x0000000000000000000000000000000000008001")

DEPOSIT_GAS_PER_PUBDATA_LIMIT = 800

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
    name_encoded = encode(['string'], [name])
    symbol_encoded = encode(['string'], [symbol])
    decimals_encoded = encode(['uint256'], [decimals])

    return encode(['bytes', 'bytes', 'bytes'], [name_encoded, symbol_encoded, decimals_encoded])


def apply_l1_to_l2_alias(address: HexStr):
    result = (int(L1_TO_L2_ALIAS_OFFSET, 16) + int(address, 16)) % ADDRESS_MODULO
    return Web3.to_hex(result)

def undo_l1_to_l2_alias(address: HexStr):
    result = int(L1_TO_L2_ALIAS_OFFSET, 16) - int(address, 16)
    if result < 0:
        result += ADDRESS_MODULO

    return Web3.to_hex(result)


# def estimate_default_bridge_deposit_l2_gas(token: HexStr,
#                                            amount: int,
#                                            to: HexStr,
#                                            provider_l1: Web3,
#                                            provider_l2: Web3,
#                                            l1_account: BaseAccount,
#                                            gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT,
#                                            from_: HexStr = None) -> int:
#     if from_ is None:
#         account = Account.create()
#         from_ = account.address
#
#     if token == ADDRESS_DEFAULT or token == L2_ETH_TOKEN_ADDRESS:
#         func_call = TxFunctionCall(to=to,
#                                    from_=from_,
#                                    value=amount,
#                                    gas_per_pub_data=gas_per_pubdata_byte)
#         return provider_l2.zksync.zks_estimate_l1_to_l2_execute(func_call.tx)
#     else:
#         bridge_addresses = provider_l2.zksync.zks_get_bridge_contracts()
#         l1_weth_bridge = L1Bridge(bridge_addresses.weth_bridge_l1,
#                                   provider_l2,
#                                   l1_account)
#         l2_weth_token = l1_weth_bridge.l2_token_address(token)
#
#         if l2_weth_token == ADDRESS_DEFAULT:
#             l1_bridge_address = bridge_addresses.weth_bridge_l1
#             l2_bridge_address = bridge_addresses.weth_bridge_l2
#             bridge_data = "0x"
#         else:
#             l1_bridge_address = bridge_addresses.erc20_l1_default_bridge
#             l2_bridge_address = bridge_addresses.erc20_l2_default_bridge
#             token_contract = provider_l2.zksync.contract(token, abi=get_erc20_abi())
#             bridge_data = get_custom_bridge_data(token_contract)
#
#     return estimate_custom_bridge_deposit_l2_gas(provider_l2,
#                                                  l1_bridge_address,
#                                                  l2_bridge_address,
#                                                  token,
#                                                  amount,
#                                                  to,
#                                                  from_,
#                                                  bridge_data,
#                                                  l1_account,
#                                                  gas_per_pubdata_byte)
#
# def estimate_custom_bridge_deposit_l2_gas(provider_l2: Web3,
#                                           l1_bridge_address: HexStr,
#                                           l2_bridge_address: HexStr,
#                                           token: HexStr,
#                                           amount: int,
#                                           to: HexStr,
#                                           from_: HexStr,
#                                           bridge_data: bytes,
#                                           l1_account: BaseAccount,
#                                           gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT) -> int:
#     calldata = get_erc_20_call_data(token, from_, to, amount, bridge_data, provider_l2, l1_account)
#     tx = TxFunctionCall(from_=apply_l1_to_l2_alias(l1_bridge_address),
#                         to=l2_bridge_address,
#                         data=calldata,
#                         gas_per_pub_data=gas_per_pubdata_byte)
#
#     return provider_l2.zksync.zks_estimate_l1_to_l2_execute(tx.tx)
#
# def get_erc_20_call_data(l1_token_address: HexStr,
#                           l1_sender: HexStr,
#                           l2_receiver: HexStr,
#                           amount: int,
#                           bridge_data: bytes,
#                           provider_l2: Web3,
#                           l1_account: BaseAccount) -> HexStr:
#         l2_bridge = L2Bridge(l1_token_address, provider_l2, l1_account)
#         return l2_bridge.finalize_deposit(l1_sender, l2_receiver, l1_token_address, amount, bridge_data)


class RecommendedGasLimit(IntEnum):
    DEPOSIT = 10000000
    EXECUTE = 620000
    ERC20_APPROVE = 50000
    DEPOSIT_GAS_PER_PUBDATA_LIMIT = 800
    L1_RECOMMENDED_ETH_DEPOSIT_GAS_LIMIT = 200000
    L1_RECOMMENDED_MIN_ERC_20_DEPOSIT_GAS_LIMIT = 400000

