from dataclasses import dataclass
from hashlib import sha256
from typing import Union, Optional
import sys
import rlp
from eth_account.datastructures import SignedMessage
from eth_typing import ChecksumAddress, HexStr
from rlp.sedes import big_endian_int, binary
from rlp.sedes import List as rlpList

from web3.types import Nonce
from protocol.request.request_types import EIP712Meta
from eip712_structs import EIP712Struct, Address, Uint, Bytes, Array
from protocol.core.utils import get_data, hash_byte_code, encode_address

# Special case: Length of 0 means a dynamic bytes type
DynamicBytes = Bytes(0)


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
        class Transaction(EIP712Struct):
            pass

        setattr(Transaction, 'txType',                   Uint(256))
        setattr(Transaction, 'from',                     Uint(256))
        setattr(Transaction, 'to',                       Uint(256))
        setattr(Transaction, 'ergsLimit',                Uint(256))
        setattr(Transaction, 'ergsPerPubdataByteLimit',  Uint(256))
        setattr(Transaction, 'maxFeePerErg',             Uint(256))
        setattr(Transaction, 'maxPriorityFeePerErg',     Uint(256))
        setattr(Transaction, 'paymaster',                Uint(256))
        setattr(Transaction, 'nonce',                    Uint(256))
        setattr(Transaction, 'value',                    Uint(256))
        setattr(Transaction, 'data',                     DynamicBytes)
        setattr(Transaction, 'factoryDeps',              Array(Bytes(32)))
        setattr(Transaction, 'paymasterInput',           DynamicBytes)

        paymaster: int = 0
        paymaster_params = self.meta.paymaster_params
        if paymaster_params is not None and paymaster_params.paymaster is not None:
            paymaster = int(paymaster_params.paymaster, 16)

        data = get_data(self.data)

        factory_deps = self.meta.factory_deps
        factory_deps_hashes = b''
        if factory_deps is not None and len(factory_deps):
            factory_deps_hashes = [hash_byte_code(bytecode) for bytecode in factory_deps]

        paymaster_input = b''
        if paymaster_params is not None and \
                paymaster_params.paymaster_input is not None:
            paymaster_input = paymaster_params.paymaster_input

        kwargs = {
            'txType': self.EIP_712_TX_TYPE,
            'from': int(self.from_, 16),
            'to': int(self.to, 16),
            'ergsLimit': self.gas_limit,
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
        return Transaction(**kwargs)


class Transaction712Encoder:
    EIP_712_TX_TYPE = b'\x71'

    @classmethod
    def encode(cls, tx712: Transaction712, signature: Optional[SignedMessage] = None) -> bytes:
        meta = tx712.meta

        factory_deps_data = []
        factory_deps_elements = None
        factory_deps = meta.factory_deps
        if factory_deps is not None and len(factory_deps) > 0:
            factory_deps_data = factory_deps
            factory_deps_elements = [binary for _ in range(len(factory_deps_data))]

        paymaster_params_data = []
        paymaster_params_elements = None
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

        custom_signature = meta.custom_signature
        if custom_signature is not None:
            rlp_signature = custom_signature
        elif signature is not None:
            rlp_signature = signature.signature
        else:
            raise RuntimeError("Custom signature and signature can't be None both")

        representation_params = {
            "nonce": tx712.nonce,
            "maxPriorityFeePerGas": tx712.maxPriorityFeePerGas,
            "maxFeePerGas": tx712.maxFeePerGas,
            "gasLimit": tx712.gas_limit,
            "to": encode_address(tx712.to),
            "value": tx712.value,
            "data": get_data(tx712.data),
            "chain_id": tx712.chain_id,
            "unknown1": b'',
            "unknown2": b'',
            "chain_id2": tx712.chain_id,
            "from": encode_address(tx712.from_),
            "ergsPerPubdata": meta.ergs_per_pub_data,
            "factoryDeps": factory_deps_data,
            "signature": rlp_signature,
            "paymaster_params": paymaster_params_data
        }
        representation = InternalRepresentation(**representation_params)
        encoded_rlp = rlp.encode(representation, infer_serializer=True, cache=False)
        return cls.EIP_712_TX_TYPE + encoded_rlp
