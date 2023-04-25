import os
from dataclasses import dataclass
from enum import IntEnum, auto
from eth_typing import HexStr
from eth_utils import remove_0x_prefix


class EnvPrivateKey:
    def __init__(self, env: str):
        env = os.getenv(env, None)
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


LOCAL_ENV = TestEnvironment(EnvType.LOCAL_HOST, "http://127.0.0.1:3050", "http://127.0.0.1:8545")
TESTNET = TestEnvironment(EnvType.TESTNET, "https://zksync2-testnet.zksync.dev", "https://rpc.ankr.com/eth_goerli")
