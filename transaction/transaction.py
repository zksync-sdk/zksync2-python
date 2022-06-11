from abc import ABC
from dataclasses import dataclass
from typing import Optional

from eip712_structs import EIP712Struct, Address, Uint, Bytes
from eth_typing import HexStr

from zk_types.zk_types import Fee, TokenAddress
from eth_utils.crypto import keccak_256


# from eth_typing.evm import Address as ethAddress
# from eth_typing.evm import Nonce

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


@dataclass
class TransactionBase:
    address: Address()
    fee: Fee
    nonce: Uint(32)

    def transaction_request(self) -> TransactionRequest:
        raise NotImplementedError


class Execute(TransactionBase, ABC):

    def __int__(self, contract_address: HexStr, call_data: bytes, initiator_address: HexStr, fee: Fee, nonce: int):
        super(Execute, self).__init__(address=initiator_address, fee=fee, nonce=nonce)
        self.contract_address = contract_address
        self.call_data = call_data

    def transaction_request(self) -> TransactionRequest:
        return TransactionRequest(
            to=self.contract_address,
            nonce=self.nonce,
            # TODO: default value, check it
            value=Uint(256),
            data=self.call_data,
            # TODO: here it's hex bytes, need to convert to int ???
            gasPrice=int.from_bytes(self.fee.ergsPriceLimit, byteorder='big', signed=False),
            # TODO: here it's hex bytes, need to convert to int ???
            gasLimit=int.from_bytes(self.fee.ergsLimit, byteorder='big', signed=False),
            ergsPerStorage=int.from_bytes(self.fee.ergsPerStorageLimit, byteorder='big', signed=False),
            ergsPerPubdata=int.from_bytes(self.fee.ergsPerPubdataLimit, byteorder='big', signed=False),
            feeToken=self.fee.feeToken,
            # TODO: default address, check it
            withdrawToken=Address()
        )


class DeployContract(TransactionBase, ABC):

    def __init__(self, bytecode: bytes, call_data: Optional[bytes], initiator_address: HexStr, fee: Fee, nonce: int):
        super(DeployContract, self).__init__(initiator_address, fee, nonce)
        self.main_contract_hash = keccak_256(bytecode)
        if call_data is None:
            call_data = b'\0' * 7 + b'\1' + b'\0' * 24
        self.call_data = call_data
        # this.factoryDeps = new byte[][] { bytecode };

    def _get_input(self):
        return self.main_contract_hash + self.call_data

    def transaction_request(self) -> TransactionRequest:
        return TransactionRequest(
            # TODO: check for default address, must be
            to=Address(),
            nonce=self.nonce,
            # TODO: check that it's default value
            value=Uint(256),
            data=self._get_input(),
            # TODO: here it's hex bytes, need to convert to int ???
            gasPrice=int.from_bytes(self.fee.ergsPriceLimit, byteorder='big', signed=False),
            # TODO: here it's hex bytes, need to convert to int ???
            gasLimit=int.from_bytes(self.fee.ergsLimit, byteorder='big', signed=False),
            ergsPerStorage=int.from_bytes(self.fee.ergsPerStorageLimit, byteorder='big', signed=False),
            ergsPerPubdata=int.from_bytes(self.fee.ergsPerPubdataLimit, byteorder='big', signed=False),
            feeToken=self.fee.feeToken,
            # TODO: default address, check it
            withdrawToken=Address()
        )


class Withdraw(TransactionBase, ABC):

    def __init__(self,
                 token_address: TokenAddress, to: HexStr, amount: int,
                 initiator_address: HexStr, fee: Fee, nonce: int):
        super(Withdraw, self).__init__(initiator_address, fee, nonce)
        self.token_address = token_address
        self.to: Address() = to
        self.amount: Uint(256) = amount

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

