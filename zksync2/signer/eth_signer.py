from abc import abstractmethod, ABC

import web3
from eth_account.datastructures import SignedMessage
from eth_account.messages import encode_defunct, SignableMessage
from eth_account.signers.base import BaseAccount
from eth_typing import ChecksumAddress, HexStr
from eth_utils import keccak

from zksync2.eip712 import make_domain, EIP712Struct


class EthSignerBase:
    @abstractmethod
    def sign_typed_data(self, typed_data: EIP712Struct, domain=None) -> SignedMessage:
        raise NotImplemented

    @abstractmethod
    def verify_typed_data(self, sig: HexStr, typed_data: EIP712Struct) -> bool:
        raise NotImplemented


class PrivateKeyEthSigner(EthSignerBase, ABC):
    _NAME = "zkSync"
    _VERSION = "2"

    def __init__(self, creds: BaseAccount, chain_id: int):
        self.credentials = creds
        self.chain_id = chain_id
        self.default_domain = make_domain(
            name=self._NAME, version=self._VERSION, chainId=self.chain_id
        )

    @staticmethod
    def get_default_domain(chain_id: int):
        return make_domain(
            name=PrivateKeyEthSigner._NAME,
            version=PrivateKeyEthSigner._VERSION,
            chainId=chain_id,
        )

    @property
    def address(self) -> ChecksumAddress:
        return self.credentials.address

    @property
    def domain(self):
        return self.default_domain

    def typed_data_to_signed_bytes(
        self, typed_data: EIP712Struct, domain=None
    ) -> SignableMessage:
        d = domain
        if d is None:
            d = self.domain
        msg = typed_data.signable_bytes(d)
        return encode_defunct(msg)

    def sign_typed_data(self, typed_data: EIP712Struct, domain=None) -> SignedMessage:
        singable_message = self.typed_data_to_signed_bytes(typed_data, domain)
        msg_hash = keccak(singable_message.body)
        return self.credentials.unsafe_sign_hash(msg_hash)

    def verify_typed_data(
        self, sig: HexStr, typed_data: EIP712Struct, domain=None
    ) -> bool:
        singable_message = self.typed_data_to_signed_bytes(typed_data, domain)
        msg_hash = keccak(singable_message.body)
        address = web3.Account._recover_hash(message_hash=msg_hash, signature=sig)
        return address.lower() == self.address.lower()

    def sign_message(self, message: bytes) -> SignedMessage:
        msg_hash = keccak(message)
        return self.credentials.unsafe_sign_hash(msg_hash)
