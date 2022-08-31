import dataclasses
from dataclasses import dataclass
from hashlib import sha256
from typing import Union, Optional
import sys
import rlp
from eth_account.datastructures import SignedMessage
from eth_typing import Address, ChecksumAddress, HexStr
from rlp.sedes import big_endian_int, binary
from rlp.sedes import List as rlpList

from web3.types import Nonce
from protocol.request.request_types import EIP712Meta
from eip712_structs import EIP712Struct, Address, Uint, Bytes, Array


# TxParams = TypedDict("TxParams", {
#     "chainId": int,
#     "data": Union[bytes, HexStr],
#     # addr or ens
#     "from": Union[Address, ChecksumAddress, str],
#     "gas": Wei,
#     # legacy pricing
#     "gasPrice": Wei,
#     # dynamic fee pricing
#     "maxFeePerGas": Union[str, Wei],
#     "maxPriorityFeePerGas": Union[str, Wei],
#     "nonce": Nonce,
#     # addr or ens
#     "to": Union[Address, ChecksumAddress, str],
#     "type": Union[int, HexStr],
#     "value": Wei,
# }, total=False)

def int_to_bytes(x: int) -> bytes:
    return x.to_bytes((x.bit_length() + 7) // 8, byteorder=sys.byteorder)


def get_data(data: Union[bytes, HexStr]) -> bytes:
    if isinstance(data, bytes):
        return data
    if data.startswith("0x"):
        data = data[2:]
    return bytes.fromhex(data)


def _get_v(signature) -> bytes:
    v_bytes = bytes()
    # TODO: getV[0] is big endian or little , and what is the bytes amount??
    if signature.v != 0:
        v_bytes = int_to_bytes(signature.v)
    return v_bytes


def _encode_address(addr: Union[Address, ChecksumAddress, str]) -> bytes:
    if len(addr) == 0:
        return bytes()
    if isinstance(addr, bytes):
        return addr
    if addr.startswith("0x"):
        addr = addr[2:]
    return bytes.fromhex(addr)


def _hash_byte_code(bytecode: bytes) -> bytes:
    bytecode_hash = bytes.fromhex(sha256(bytecode).hexdigest())
    bytecode_size = int(len(bytecode_hash) / 32)
    if bytecode_size > 2 ** 16:
        raise OverflowError("_hash_byte_code, bytecode length must be less than 2^16")
    ret = bytecode_size.to_bytes(2, byteorder='big') + bytecode_hash[2:]
    return ret


@dataclass
class Transaction712:
    EIP_712_TX_TYPE = 113

    chain_id: int
    nonce: Nonce
    gas_limit: int
    to: Union[Address, ChecksumAddress, str]
    value: int
    data: Union[bytes, HexStr]
    maxPriorityFeePerGas: int
    maxFeePerGas: int
    from_: Union[bytes, HexStr]
    meta: EIP712Meta

    def to_eip712_struct(self) -> EIP712Struct:
        class InternalRepresentation(EIP712Struct):
            pass

        setattr(InternalRepresentation, 'txType',                   Uint(256))
        setattr(InternalRepresentation, 'from',                     Uint(256))
        setattr(InternalRepresentation, 'to',                       Uint(256))
        setattr(InternalRepresentation, 'ergsLimit',                Uint(256))
        setattr(InternalRepresentation, 'ergsPerPubdataByteLimit',  Uint(256))
        setattr(InternalRepresentation, 'maxFeePerErg',             Uint(256))
        setattr(InternalRepresentation, 'maxPriorityFeePerErg',     Uint(256))
        setattr(InternalRepresentation, 'paymaster',                Uint(256))
        setattr(InternalRepresentation, 'nonce',                    Uint(256))
        setattr(InternalRepresentation, 'value',                    Uint(256))
        setattr(InternalRepresentation, 'data',                     Bytes)
        setattr(InternalRepresentation, 'factoryDeps',              Array(Bytes(32)))
        setattr(InternalRepresentation, 'paymasterInput',           Bytes())

        paymaster: int = 0
        # paymaster_params = self.meta["paymasterParams"]
        paymaster_params = self.meta.paymaster_params
        if paymaster_params is not None and paymaster_params.paymaster is not None:
            paymaster = int(paymaster_params.paymaster, 16)

        data = get_data(self.data)
        if not data:
            data = b'00'
        # factory_deps = self.meta["factoryDeps"]
        factory_deps = self.meta.factory_deps
        factory_deps_hashes = b''
        if factory_deps is not None and len(factory_deps):
            factory_deps_hashes = [_hash_byte_code(bytecode) for bytecode in factory_deps]

        paymaster_input = b''
        if paymaster_params is not None and \
                paymaster_params.paymaster_input is not None:
            paymaster_input = paymaster_params.paymaster_input

        kwargs = {
            'txType': self.EIP_712_TX_TYPE,
            'from': int(self.from_, 16),
            'to': int(self.to, 16),
            'ergsLimit': self.gas_limit,
            # 'ergsPerPubdataByteLimit': self.meta["ergsPerPubdata"],
            'ergsPerPubdataByteLimit': self.meta.ergs_per_pub_data,
            'maxFeePerErg': self.maxFeePerGas,
            'maxPriorityFeePerErg': self.maxPriorityFeePerGas,
            'paymaster': paymaster,
            'nonce': self.nonce,
            'value': self.value,
            'data': data,
            'factoryDeps': factory_deps_hashes,
            'paymasterInput': paymaster_input
        }
        return InternalRepresentation(**kwargs)


class Transaction712Encoder:
    EIP_712_TX_TYPE = b'\x71'

    @classmethod
    def encode(cls, tx712: Transaction712, signature: Optional[SignedMessage] = None) -> bytes:
        meta = tx712.meta

        factory_deps_data = []
        factory_deps_elements = None
        # factory_deps = meta["factoryDeps"]
        factory_deps = meta.factory_deps
        if factory_deps is not None and len(factory_deps) > 0:
            factory_deps_data = factory_deps
            factory_deps_elements = [binary for _ in range(len(factory_deps_data))]

        paymaster_params_data = []
        paymaster_params_elements = None
        # paymaster_params = meta["paymasterParams"]
        paymaster_params = meta.paymaster_params
        if paymaster_params is not None and \
                paymaster_params.paymaster is not None and \
                paymaster_params.paymaster_input is not None:
            paymaster_params_data = [
                bytes.fromhex(paymaster_params.paymaster),
                paymaster_params.paymaster_input
            ]
            paymaster_params_elements = [binary, binary]

        class InternalRepresentation(rlp.Serializable):
            fields = [
                ('nonce', big_endian_int),
                ('maxPriorityFeePerGas', big_endian_int),
                ('maxFeePerGas', big_endian_int),
                ('gasLimit', big_endian_int),
                ('to', binary),
                ('value', big_endian_int),
                ('data', binary),
                ('chain_id', big_endian_int),
                ('unknown1', binary),
                ('unknown2', binary),
                ('chain_id2', big_endian_int),
                ('from', binary),
                ('ergsPerPubdata', big_endian_int),
                ('factoryDeps', rlpList(elements=factory_deps_elements, strict=False)),
                ('signature', binary),
                ('paymaster_params', rlpList(elements=paymaster_params_elements, strict=False))
            ]

        # custom_signature = meta["customSignature"]
        custom_signature = meta.custom_signature
        if custom_signature is not None:
            rlp_signature = custom_signature
        elif signature is not None:
            rlp_signature = int_to_bytes(signature.r) + int_to_bytes(signature.s) + int_to_bytes(signature.v)
            # rlp_signature = bytes.fromhex("")
        else:
            raise RuntimeError("Custom signature and signature can't be None both")

        representation_params = {
            "nonce": tx712.nonce,
            "maxPriorityFeePerGas": tx712.maxPriorityFeePerGas,
            "maxFeePerGas": tx712.maxFeePerGas,
            "gasLimit": tx712.gas_limit,
            "to": _encode_address(tx712.to),
            "value": tx712.value,
            "data": get_data(tx712.data),
            "chain_id": tx712.chain_id,
            "unknown1": b'',
            "unknown2": b'',
            "chain_id2": tx712.chain_id,
            "from": _encode_address(tx712.from_),
            # "ergsPerPubdata": meta["ergsPerPubdata"],
            "ergsPerPubdata": meta.ergs_per_pub_data,
            "factoryDeps": factory_deps_data,
            "signature": rlp_signature,
            "paymaster_params": paymaster_params_data
        }
        representation = InternalRepresentation(**representation_params)
        encoded_rlp = rlp.encode(representation, infer_serializer=True, cache=False)
        return cls.EIP_712_TX_TYPE + encoded_rlp
