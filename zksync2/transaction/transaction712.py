from abc import ABC
from dataclasses import dataclass
from typing import Union, Optional, List
import rlp
from eth_account.datastructures import SignedMessage
from eth_typing import ChecksumAddress, HexStr
from rlp.sedes import big_endian_int, binary
from rlp.sedes import List as rlpList
from web3 import Web3

from web3.types import Nonce

from zksync2.manage_contracts.contract_deployer import ContractDeployer
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.module.request_types import EIP712Meta, TransactionType, Transaction as ZkTx

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
            "ergsPerPubdata": self.meta.ergs_per_pub_data,
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


class TxBase(ABC):

    def __init__(self, trans: ZkTx):
        self.tx_: ZkTx = trans

    @property
    def tx(self) -> ZkTx:
        return self.tx_

    def tx712(self, estimated_gas: int) -> Transaction712:
        return Transaction712(chain_id=self.tx["chain_id"],
                              nonce=Nonce(self.tx["nonce"]),
                              gas_limit=estimated_gas,
                              to=self.tx["to"],
                              value=self.tx["value"],
                              data=self.tx["data"],
                              maxPriorityFeePerGas=self.tx["maxPriorityFeePerGas"],
                              maxFeePerGas=self.tx["gasPrice"],
                              from_=self.tx["from"],
                              meta=self.tx["eip712Meta"])


class TxFunctionCall(TxBase, ABC):

    def __init__(self,
                 chain_id: int,
                 nonce: int,
                 from_: HexStr,
                 to: HexStr,
                 value: int = 0,
                 data: HexStr = HexStr("0x"),
                 gas_limit: int = 0,
                 gas_price: int = 0,
                 max_priority_fee_per_gas=100000000):
        default_meta = EIP712Meta()
        super(TxFunctionCall, self).__init__(
            trans={
                "chain_id": chain_id,
                "nonce": nonce,
                "from": from_,
                "to": to,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "value": value,
                "data": data,
                "transactionType": TransactionType.EIP_712_TX_TYPE.value,
                "eip712Meta": default_meta
            })


class TxCreateContract(TxBase, ABC):

    def __init__(self,
                 web3: Web3,
                 chain_id: int,
                 nonce: int,
                 from_: HexStr,
                 gas_limit: int,
                 gas_price: int,
                 bytecode: bytes,
                 deps: List[bytes] = None,
                 call_data: Optional[bytes] = None,
                 value: int = 0,
                 max_priority_fee_per_gas=100000000,
                 salt: Optional[bytes] = None):

        contract_deployer = ContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create(bytecode=bytecode,
                                                              call_data=call_data,
                                                              salt_data=salt)
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)
        eip712_meta = EIP712Meta(ergs_per_pub_data=EIP712Meta.ERGS_PER_PUB_DATA_DEFAULT,
                                 custom_signature=None,
                                 factory_deps=factory_deps,
                                 paymaster_params=None)

        super(TxCreateContract, self).__init__(trans={
            "chain_id": chain_id,
            "nonce": nonce,
            "from": from_,
            "to": Web3.toChecksumAddress(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
            "gas": gas_limit,
            "gasPrice": gas_price,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "value": value,
            "data": HexStr(generated_call_data),
            "transactionType": TransactionType.EIP_712_TX_TYPE.value,
            "eip712Meta": eip712_meta
        })


class TxCreate2Contract(TxBase, ABC):

    def __init__(self,
                 web3: Web3,
                 chain_id: int,
                 nonce: int,
                 from_: HexStr,
                 gas_limit: int,
                 gas_price: int,
                 bytecode: bytes,
                 deps: List[bytes] = None,
                 call_data: Optional[bytes] = None,
                 value: int = 0,
                 max_priority_fee_per_gas=100000000,
                 salt: Optional[bytes] = None
                 ):
        contract_deployer = ContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create2(bytecode=bytecode,
                                                               call_data=call_data,
                                                               salt=salt)
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)

        eip712_meta = EIP712Meta(ergs_per_pub_data=EIP712Meta.ERGS_PER_PUB_DATA_DEFAULT,
                                 custom_signature=None,
                                 factory_deps=factory_deps,
                                 paymaster_params=None)
        super(TxCreate2Contract, self).__init__(trans={
            "chain_id": chain_id,
            "nonce": nonce,
            "from": from_,
            "to": Web3.toChecksumAddress(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
            "gas": gas_limit,
            "gasPrice": gas_price,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "value": value,
            "data": HexStr(generated_call_data),
            "transactionType": TransactionType.EIP_712_TX_TYPE.value,
            "eip712Meta": eip712_meta
        })


