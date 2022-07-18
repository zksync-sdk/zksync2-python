from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
from eip712_structs import EIP712Struct, Address, Uint, Bytes
from eth_typing import HexStr
# from transaction712 import Transaction712
from transaction.misc import Transaction712Constants
from zk_types.zk_types import Fee, TokenAddress, Transaction, Eip712Meta
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

    def to_transaction(self) -> Transaction:
        raise NotImplementedError

    def set_fee(self, new_fee: Fee):
        self.fee = new_fee


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

    def to_transaction(self) -> Transaction:
        eip: Eip712Meta = {
            "feeToken": self.fee.feeToken,
            "ergsPerStorage": HexStr(self.fee.ergsPerStorageLimit.hex()),
            "ergsPerPubdata": HexStr(self.fee.ergsPerPubdataLimit.hex()),
            "withdrawToken": "",
            "factoryDeps": []
        }
        tx: Transaction = {
            "from": self.address,
            "to":  self.contract_address,
            "gas": HexStr(self.fee.ergsLimit.hex()),
            "gasPrice": HexStr(self.fee.ergsPriceLimit.hex()),
            "value": HexStr("0x0"),
            "data": HexStr(self.call_data.hex()),
            "transactionType": HexStr(Transaction712Constants.EIP_712_TX_TYPE.value.hex()),
            "eip712Meta": eip
        }
        return tx


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

    def to_transaction(self) -> Transaction:
        eip: Eip712Meta = {
            "feeToken": self.fee.feeToken,
            "ergsPerStorage": HexStr(self.fee.ergsPerStorageLimit.hex()),
            "ergsPerPubdata": HexStr(self.fee.ergsPerPubdataLimit.hex()),
            "withdrawToken": "",
            "factoryDeps": self.factory_deps

        }
        tx: Transaction = {
            "from": self.address,
            "to": HexStr(self.DEFAULT_ADDRESS),
            "gas": HexStr(self.fee.ergsLimit.hex()),
            "gasPrice": HexStr(self.fee.ergsPriceLimit.hex()),
            "value": HexStr("0x0"),
            "data": HexStr(self._get_input().hex()),
            "transactionType": HexStr(Transaction712Constants.EIP_712_TX_TYPE.value.hex()),
            "eip712Meta": eip
        }
        return tx


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

    def to_transaction(self) -> Transaction:
        eip: Eip712Meta = {
            "feeToken": self.fee.feeToken,
            "ergsPerStorage": HexStr(self.fee.ergsPerStorageLimit.hex()),
            "ergsPerPubdata": HexStr(self.fee.ergsPerPubdataLimit.hex()),
            "withdrawToken": self.token_address,
            "factoryDeps": []
        }
        tx: Transaction = {
            "from": self.address,
            "to":  self.to,
            "gas": HexStr(self.fee.ergsLimit.hex()),
            "gasPrice": HexStr(self.fee.ergsPriceLimit.hex()),
            "value": HexStr(hex(self.amount)),
            "data": HexStr(""),
            "transactionType": HexStr(Transaction712Constants.EIP_712_TX_TYPE.value.hex()),
            "eip712Meta": eip
        }
        return tx



