import json

import web3
from abc import abstractmethod, ABC
from eip712_structs import make_domain, EIP712Struct
from eth_account.datastructures import SignedMessage
from eth_typing import ChecksumAddress, HexStr
from eth_utils import keccak
from eth_account.signers.local import LocalAccount
from eth_account.messages import encode_defunct, SignableMessage
from crypto.eth_account_patch.encode_structed_data import encode_structured_data

from eth_utils.curried import to_bytes


class EthSignerBase:

    @abstractmethod
    def get_address(self) -> ChecksumAddress:
        raise NotImplementedError

    @abstractmethod
    def get_domain(self):
        raise NotImplemented

    @abstractmethod
    def sign_message(self, msg: str) -> HexStr:
        raise NotImplemented

    def verify_signature(self, sig: HexStr, msg: bytes) -> bool:
        raise NotImplemented

    def sign_typed_data(self, typed_data: EIP712Struct) -> HexStr:
        raise NotImplemented

    def verify_typed_signature(self, sig: HexStr, typed_data: EIP712Struct) -> bool:
        raise NotImplemented


class PrivateKeyEthSigner(EthSignerBase, ABC):
    _NAME = "zkSync"
    _VERSION = "2"

    def __init__(self, creds: LocalAccount, chain_id: int):
        self.credentials = creds
        self.chain_id = chain_id

    def get_address(self) -> ChecksumAddress:
        return self.credentials.address

    def get_domain(self):
        default_domain = make_domain(name=self._NAME,
                                     version=self._VERSION,
                                     chainId=self.chain_id)
        return default_domain

    def sign_message(self, msg: str) -> HexStr:
        """
        INFO: message is always prefixed
        """
        message_hash = encode_defunct(to_bytes(text=msg))
        sig = self.credentials.sign_message(message_hash)
        return HexStr(sig.signature.hex())

    def verify_signature(self, signature: HexStr, msg: str):
        msg = encode_defunct(text=msg)
        address = web3.Account.recover_message(signable_message=msg, signature=signature)
        return address == self.get_address()

    def typed_data_to_signed_bytes(self, typed_data: EIP712Struct, domain=None) -> SignableMessage:
        d = domain
        if d is None:
            d = self.get_domain()
        msg = typed_data.signable_bytes(d)
        message_hash = encode_defunct(msg)
        return message_hash

    def sign_typed_data_msg_hash(self, typed_data: EIP712Struct, domain=None) -> SignedMessage:
        d = domain
        if d is None:
            d = self.get_domain()
        msg = typed_data.signable_bytes(d)
        singable_message = encode_defunct(msg)
        msg_hash = keccak(singable_message.body)
        return self.credentials.signHash(msg_hash)

    def sign_typed_data(self, typed_data: EIP712Struct, domain=None) -> SignedMessage:
        d = domain
        if d is None:
            d = self.get_domain()
        msg = typed_data.signable_bytes(d)
        message_hash = encode_defunct(msg)
        sig = self.credentials.sign_message(message_hash)
        return sig

    def verify_typed_data(self, sig: HexStr, typed_data: EIP712Struct, domain=None) -> bool:
        d = domain
        if d is None:
            d = self.get_domain()
        structured = typed_data.to_message(d)
        msg = encode_structured_data(structured)
        address = web3.Account.recover_message(signable_message=msg, signature=sig)
        return address == self.get_address()
