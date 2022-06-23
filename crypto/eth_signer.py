import json

import web3
from abc import abstractmethod, ABC
from eip712_structs import make_domain, EIP712Struct
from eth_typing import ChecksumAddress
from zk_types.zk_types import *
from eth_account.signers.local import LocalAccount
from eth_account.messages import encode_defunct, defunct_hash_message, encode_structured_data, _hash_eip191_message
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
    _ADDRESS_DEFAULT = "0x" + "0" * 40

    def __init__(self, creds: LocalAccount, chain_id: int):
        self.credentials = creds
        self.chain_id = chain_id

    def get_address(self) -> ChecksumAddress:
        return self.credentials.address

    def get_domain(self):
        default_domain = make_domain(name=self._NAME,
                                     version=self._VERSION,
                                     chainId=self.chain_id,
                                     verifyingContract=self._ADDRESS_DEFAULT)
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

    def sign_typed_data(self, typed_data: EIP712Struct, domain=None) -> HexStr:
        d = domain
        if d is None:
            d = self.get_domain()
        structured_json = typed_data.to_message_json(d)
        json_value = json.loads(structured_json)
        msg = encode_structured_data(json_value)
        sig = self.credentials.sign_message(msg)
        return HexStr(sig.signature.hex())

    def verify_typed_data(self, sig: HexStr, typed_data: EIP712Struct, domain=None) -> bool:
        d = domain
        if d is None:
            d = self.get_domain()
        structured_json = typed_data.to_message_json(d)
        json_value = json.loads(structured_json)
        msg = encode_structured_data(json_value)
        address = web3.Account.recover_message(signable_message=msg, signature=sig)
        return address == self.get_address()
