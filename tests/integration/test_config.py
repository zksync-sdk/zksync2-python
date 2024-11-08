import os
from dataclasses import dataclass
from enum import IntEnum, auto
from eth_typing import HexStr
from eth_utils import remove_0x_prefix
from web3 import Web3

from tests.unit.test_config import TestEnvironment

DAI_L1 = Web3.to_checksum_address("0x70a0F165d6f8054d0d0CF8dFd4DD2005f0AF6B55")
approval_token = Web3.to_checksum_address("0x0183Fe07a98bc036d6eb23C3943d823bcD66a90F")
paymaster_address = Web3.to_checksum_address(
    "0x594E77D36eB367b3AbAb98775c99eB383079F966"
)
multisig_address = Web3.to_checksum_address(
    "0xe56070305f425AC6F19aa319fAe11BaD25cF19A9"
)
address_1 = Web3.to_checksum_address("0x36615Cf349d7F6344891B1e7CA7C72883F5dc049")
address_2 = Web3.to_checksum_address("0xa61464658AfeAf65CccaaFD3a512b69A83B77618")
private_key_1 = "0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110"
private_key_2 = "0xac1e735be8536c6534bb4f17f06f6afc73b2b5ba84ac2cfb12f7461b20c0bbe3"


class EnvPrivateKey:
    def __init__(self, env: str):
        env = "0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110"
        if env is None:
            raise LookupError(f"Can't build key from {env}")
        self._key = bytes.fromhex(remove_0x_prefix(HexStr(env)))

    @property
    def key(self) -> bytes:
        return self._key


class EnvURL:
    def __init__(self):
        env: bool = os.getenv("IS_ETH_CHAIN", False)
        if env:
            self._env = LOCAL_ETH_ENV
        else:
            self._env = LOCAL_NON_ETH_ENV

    @property
    def env(self) -> TestEnvironment:
        return self._env


class EnvType(IntEnum):
    LOCAL_HOST = auto()
    TESTNET = auto()
    UNKNOWN = auto()


@dataclass
class TestEnvironment:
    type: EnvType
    zksync_server: str
    eth_server: str


LOCAL_ETH_ENV = TestEnvironment(
    EnvType.LOCAL_HOST, "http://127.0.0.1:15100", "http://127.0.0.1:15045"
)
LOCAL_NON_ETH_ENV = TestEnvironment(
    EnvType.LOCAL_HOST, "http://127.0.0.1:15200", "http://127.0.0.1:15045"
)
