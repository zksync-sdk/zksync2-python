from dataclasses import dataclass
from decimal import Decimal
from eth_typing import HexStr, Hash32
from typing import Union, NewType, Dict, List, Any
from hexbytes import HexBytes
from enum import Enum

ADDRESS_DEFAULT = HexStr("0x" + "0" * 40)

TokenAddress = NewType('token_address', HexStr)
TransactionHash = Union[Hash32, HexBytes, HexStr]
L2WithdrawTxHash = Union[Hash32, HexBytes, HexStr]
From = NewType("from", int)
Limit = NewType('limit', int)


class ZkBlockParams(Enum):
    COMMITTED = "committed"
    FINALIZED = "finalized"


class EthBlockParams(Enum):
    PENDING = "pending"
    LATEST = "latest"


@dataclass
class Token:
    l1_address: HexStr
    l2_address: HexStr
    symbol: str
    decimals: int

    def format_token(self, amount) -> str:
        return str(Decimal(amount) / Decimal(10) ** self.decimals)

    def is_eth(self) -> bool:
        return self.l1_address == ADDRESS_DEFAULT and self.symbol == "ETH"

    def into_decimal(self, amount: int) -> Decimal:
        return Decimal(amount).scaleb(self.decimals) // Decimal(10) ** self.decimals

    def to_int(self, amount: Union[Decimal, int]) -> int:
        if isinstance(amount, int):
            amount = Decimal(amount)
        return int(amount * (Decimal(10) ** self.decimals))

    @staticmethod
    def create_eth() -> 'Token':
        return Token(ADDRESS_DEFAULT, ADDRESS_DEFAULT, "ETH", 18)


@dataclass
class Fee:
    feeToken: TokenAddress
    ergsLimit: int
    ergsPriceLimit: int
    ergsPerPubdataLimit: int

    @classmethod
    def default_fee(cls, address: TokenAddress) -> 'Fee':
        val = cls(feeToken=address,
                  ergsLimit=0,
                  ergsPriceLimit=0,
                  ergsPerPubdataLimit=0)
        return val


@dataclass
class BridgeAddresses:
    l1_eth_default_bridge: HexStr
    l2_eth_default_bridge: HexStr
    l1_erc20_default_bridge: HexStr
    l2_erc20_default_bridge: HexStr


VmExecutionSteps = NewType("VmExecutionSteps", Any)
ContractSourceDebugInfo = NewType("ContractSourceDebugInfo", Any)


@dataclass
class VmDebugTrace:
    steps: List[VmExecutionSteps]
    sources: Dict[str, ContractSourceDebugInfo]


@dataclass
class PaymasterParams(dict):
    paymaster: HexStr
    paymaster_input: bytes
