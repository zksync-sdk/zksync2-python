from dataclasses import dataclass
from typing import Union, Optional
import rlp
from eth_account.datastructures import SignedMessage
from eth_typing import ChecksumAddress, HexStr
from eth_utils import remove_0x_prefix
from rlp.sedes import big_endian_int, binary
from rlp.sedes import List as rlpList
from web3.types import Nonce
from zksync2.module.request_types import EIP712Meta

from eip712_structs import EIP712Struct, Address, Uint, Bytes, Array
from zksync2.core.utils import to_bytes, hash_byte_code, encode_address, int_to_bytes

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

    def encode(self, signature: Optional[SignedMessage] = None) -> bytes:
        factory_deps_data = []
        factory_deps_elements = None
        factory_deps = self.meta.factory_deps
        if factory_deps is not None and len(factory_deps) > 0:
            factory_deps_data = factory_deps
            factory_deps_elements = [binary for _ in range(len(factory_deps_data))]

        paymaster_params_data = []
        paymaster_params_elements = None
        paymaster_params = self.meta.paymaster_params
        if paymaster_params is not None and \
                paymaster_params.paymaster is not None and \
                paymaster_params.paymaster_input is not None:
            paymaster_params_data = [
                bytes.fromhex(remove_0x_prefix(paymaster_params.paymaster)),
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
                ('gasPerPubdata', big_endian_int),
                ('factoryDeps', rlpList(elements=factory_deps_elements, strict=False)),
                ('signature', binary),
                ('paymaster_params', rlpList(elements=paymaster_params_elements, strict=False))
            ]

        custom_signature = self.meta.custom_signature
        if custom_signature is not None:
            rlp_signature = custom_signature
        elif signature is not None:
            rlp_signature = signature.signature
        else:
            raise RuntimeError("Custom signature and signature can't be None both")

        representation_params = {
            "nonce": self.nonce,
            "maxPriorityFeePerGas": self.maxPriorityFeePerGas,
            "maxFeePerGas": self.maxFeePerGas,
            "gasLimit": self.gas_limit,
            "to": encode_address(self.to),
            "value": self.value,
            "data": to_bytes(self.data),
            "chain_id": self.chain_id,
            "unknown1": b'',
            "unknown2": b'',
            "chain_id2": self.chain_id,
            "from": encode_address(self.from_),
            "gasPerPubdata": self.meta.gas_per_pub_data,
            "factoryDeps": factory_deps_data,
            "signature": rlp_signature,
            "paymaster_params": paymaster_params_data
        }
        representation = InternalRepresentation(**representation_params)
        encoded_rlp = rlp.encode(representation, infer_serializer=True, cache=False)
        return int_to_bytes(self.EIP_712_TX_TYPE) + encoded_rlp

    def to_eip712_struct(self) -> EIP712Struct:
        class Transaction(EIP712Struct):
            pass

        paymaster: int = 0
        paymaster_params = self.meta.paymaster_params
        if paymaster_params is not None and paymaster_params.paymaster is not None:
            paymaster = int(paymaster_params.paymaster, 16)

        data = to_bytes(self.data)

        factory_deps = self.meta.factory_deps
        factory_deps_hashes = b''
        if factory_deps is not None and len(factory_deps):
            factory_deps_hashes = tuple([hash_byte_code(bytecode) for bytecode in factory_deps])

        setattr(Transaction, 'txType',                   Uint(256))
        setattr(Transaction, 'from',                     Uint(256))
        setattr(Transaction, 'to',                       Uint(256))
        setattr(Transaction, 'gasLimit',                Uint(256))
        setattr(Transaction, 'gasPerPubdataByteLimit',   Uint(256))
        setattr(Transaction, 'maxFeePerGas',             Uint(256))
        setattr(Transaction, 'maxPriorityFeePerGas',     Uint(256))
        setattr(Transaction, 'paymaster',                Uint(256))
        setattr(Transaction, 'nonce',                    Uint(256))
        setattr(Transaction, 'value',                    Uint(256))
        setattr(Transaction, 'data',                     DynamicBytes)
        setattr(Transaction, 'factoryDeps',              Array(Bytes(32)))
        setattr(Transaction, 'paymasterInput',           DynamicBytes)

        paymaster_input = b''
        if paymaster_params is not None and \
                paymaster_params.paymaster_input is not None:
            paymaster_input = paymaster_params.paymaster_input

        kwargs = {
            'txType': self.EIP_712_TX_TYPE,
            'from': int(self.from_, 16),
            'to': int(self.to, 16),
            'gasLimit': self.gas_limit,
            'gasPerPubdataByteLimit': self.meta.gas_per_pub_data,
            'maxFeePerGas': self.maxFeePerGas,
            'maxPriorityFeePerGas': self.maxPriorityFeePerGas,
            'paymaster': paymaster,
            'nonce': self.nonce,
            'value': self.value,
            'data': data,
            'factoryDeps': factory_deps_hashes,
            'paymasterInput': paymaster_input
        }
        return Transaction(**kwargs)


