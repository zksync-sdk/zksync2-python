from abc import abstractmethod, ABC

import eth_account.account
import web3
from eth_typing import ChecksumAddress
from web3.types import Hash32, HexStr, Nonce, Wei
from zk_types.zk_types import *
from eth_account.signers.local import LocalAccount
from eth_account.messages import encode_defunct, defunct_hash_message
from eth_utils.curried import to_hex, to_bytes
from web3 import Web3


# from web3.eth import recoverHash


class EthSignerBase:

    @abstractmethod
    def get_address(self) -> ChecksumAddress:
        raise NotImplementedError

    @abstractmethod
    def get_domain(self) -> Eip712Domain:
        raise NotImplemented

    @abstractmethod
    def sign_message(self, msg: str) -> HexStr:
        raise NotImplemented

    def verify_signature(self, sig: HexStr, msg: bytes) -> bool:
        raise NotImplemented


# def get_eth_message_hash(self) -> bytes:
#     raise NotImplemented

# def get_eth_message_prefix(self, msg_len: int):
#    raise NotImplemented


class PrivateKeyEthSigner(EthSignerBase, ABC):
    _NAME = "zkSync"
    _VERSION = "2"
    # INFO: Java holds 160 length with BigInt 0 => 160/8 = 20
    _DEFAULT_ADDRESS = Address("0x00000000000000000000".encode())

    def __init__(self, creds: LocalAccount, chain_id: HexBytes):
        self.credentials = creds
        self.chain_id = chain_id

    def get_address(self) -> ChecksumAddress:
        return self.credentials.address

    def get_domain(self) -> Eip712Domain:
        default_domain = Eip712Domain(self._NAME, self._VERSION, self.chain_id, self._DEFAULT_ADDRESS)
        return default_domain

    def sign_message(self, msg: str) -> HexStr:
        """
        INFO: message is always prefixed
        """
        message_hash = encode_defunct(to_bytes(text=msg))
        sig = self.credentials.sign_message(message_hash)
        signature = sig.r.to_bytes(32, 'big') + sig.s.to_bytes(32, 'big') + sig.v.to_bytes(1, 'big')
        return HexStr(signature)

    def verify_signature(self, signature: HexStr, msg: str):
        message_hash = defunct_hash_message(text=msg)
        address = web3.Account.recoverHash(message_hash=message_hash, signature=signature)
        return address == self.get_address()
