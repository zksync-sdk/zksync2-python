import os
from dataclasses import dataclass
from enum import IntEnum, auto
from eth_typing import HexStr
from eth_utils import remove_0x_prefix


class EnvPrivateKey:
    def __init__(self, env: str):
        env = "0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110"
        if env is None:
            raise LookupError(f"Can't build key from {env}")
        self._key = bytes.fromhex(remove_0x_prefix(HexStr(env)))

    @property
    def key(self) -> bytes:
        return self._key


class EnvType(IntEnum):
    LOCAL_HOST = auto()
    TESTNET = auto()
    UNKNOWN = auto()


@dataclass
class TestEnvironment:
    type: EnvType
    zksync_server: str
    eth_server: str


LOCAL_ENV = TestEnvironment(
    EnvType.LOCAL_HOST, "http://localhost:3050", "http://127.0.0.1:8545"
)
