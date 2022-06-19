from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
from eip712_structs import EIP712Struct, Address, Uint, Bytes
from eth_typing import HexStr
from zk_types.zk_types import Fee, TokenAddress
from eth_utils.crypto import keccak_256

# TODO: check should Fee be EIP712 Struct-able or not
#       depends on this use @dataclass or EIP712 Struct-able Type


class TransactionRequest(EIP712Struct):
    to = Address()
    nonce = Uint(256)
    value = Uint(256)
    data = Bytes()
    gasPrice = Uint(256)
    gasLimit = Uint(256)
    ergsPerStorage = Uint(256)
    ergsPerPubdata = Uint(256)
    feeToken = Address()
    withdrawToken = Address()


class TransactionType(Enum):
    EXECUTE = auto()
    DEPLOY = auto()
    WITHDRAW = auto()


@dataclass
class TransactionBase:
    address: Address()
    fee: Fee
    nonce: Uint(32)

    DEFAULT_ADDRESS = "0x" + "0"*40

    def transaction_request(self) -> TransactionRequest:
        raise NotImplementedError

    def get_type(self) -> TransactionType:
        raise NotImplementedError


class Execute(TransactionBase, ABC):

    def __init__(self, contract_address: HexStr, call_data: bytes, initiator_address: HexStr, fee: Fee, nonce: int):
        super(Execute, self).__init__(initiator_address, fee, nonce)
        self.contract_address = contract_address
        self.call_data = call_data

    def transaction_request(self) -> TransactionRequest:
        return TransactionRequest(
            to=self.contract_address,
            nonce=self.nonce,
            # TODO: default value, check it
            # value=Uint(256),
            value=0,
            data=self.call_data,
            # TODO: here it's hex bytes, need to convert to int ???
            gasPrice=int.from_bytes(self.fee.ergsPriceLimit, byteorder='big', signed=False),
            # TODO: here it's hex bytes, need to convert to int ???
            gasLimit=int.from_bytes(self.fee.ergsLimit, byteorder='big', signed=False),
            ergsPerStorage=int.from_bytes(self.fee.ergsPerStorageLimit, byteorder='big', signed=False),
            ergsPerPubdata=int.from_bytes(self.fee.ergsPerPubdataLimit, byteorder='big', signed=False),
            feeToken=self.fee.feeToken,
            # TODO: default address, check it
            withdrawToken=self.DEFAULT_ADDRESS
        )

    def get_type(self) -> TransactionType:
        return TransactionType.EXECUTE


class DeployContract(TransactionBase, ABC):

    def __init__(self, bytecode: bytes, call_data: Optional[bytes], initiator_address: HexStr, fee: Fee, nonce: int):
        super(DeployContract, self).__init__(initiator_address, fee, nonce)
        self.main_contract_hash = keccak_256(bytecode)
        if call_data is None:
            call_data = bytes(b'\0' * 8) + bytes(b'\1') + bytes(b'\0' * 23)
        self.call_data = call_data
        self.factory_deps = [bytecode]

    def _get_input(self) -> bytes:
        return self.main_contract_hash + self.call_data

    def transaction_request(self) -> TransactionRequest:
        return TransactionRequest(
            # TODO: check for default address, must be
            # to=Address(),
            to=self.DEFAULT_ADDRESS,
            nonce=self.nonce,
            # TODO: check that it's default value
            # value=Uint(256),
            value=0,
            data=self._get_input(),
            # TODO: here it's hex bytes, need to convert to int ???
            gasPrice=int.from_bytes(self.fee.ergsPriceLimit, byteorder='big', signed=False),
            # TODO: here it's hex bytes, need to convert to int ???
            gasLimit=int.from_bytes(self.fee.ergsLimit, byteorder='big', signed=False),
            ergsPerStorage=int.from_bytes(self.fee.ergsPerStorageLimit, byteorder='big', signed=False),
            ergsPerPubdata=int.from_bytes(self.fee.ergsPerPubdataLimit, byteorder='big', signed=False),
            feeToken=self.fee.feeToken,
            # TODO: default address, check it
            withdrawToken=self.DEFAULT_ADDRESS
        )

    def get_type(self) -> TransactionType:
        return TransactionType.DEPLOY


class Withdraw(TransactionBase, ABC):

    def __init__(self,
                 token_address: TokenAddress, to: HexStr, amount: int,
                 initiator_address: HexStr, fee: Fee, nonce: int):
        super(Withdraw, self).__init__(initiator_address, fee, nonce)
        self.token_address = token_address
        self.to = to
        self.amount = amount

    def transaction_request(self) -> TransactionRequest:
        return TransactionRequest(
            to=self.to,
            nonce=self.nonce,
            value=self.amount,
            data=bytes(),
            # TODO: here it's hex bytes, need to convert to int ???
            gasPrice=int.from_bytes(self.fee.ergsPriceLimit, byteorder='big', signed=False),
            # TODO: here it's hex bytes, need to convert to int ???
            gasLimit=int.from_bytes(self.fee.ergsLimit, byteorder='big', signed=False),
            ergsPerStorage=int.from_bytes(self.fee.ergsPerStorageLimit, byteorder='big', signed=False),
            ergsPerPubdata=int.from_bytes(self.fee.ergsPerPubdataLimit, byteorder='big', signed=False),
            feeToken=self.fee.feeToken,
            withdrawToken=self.token_address
        )

    def get_type(self) -> TransactionType:
        return TransactionType.WITHDRAW



