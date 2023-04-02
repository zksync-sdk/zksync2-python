from dataclasses import dataclass
from enum import IntEnum, auto

PRIVATE_KEY2 = bytes.fromhex("fd1f96220fa3a40c46d65f81d61dd90af600746fd47e5c82673da937a48b38ef")
PRIVATE_KEY_BOB = bytes.fromhex("ba6852a8a14cd3c72f6cab8c08f70d033d5d1a56646ab04b4cf54c01cb7204dc")


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
