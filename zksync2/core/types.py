from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Union, NewType, Dict, List, Any, Optional

from eth_typing import HexStr, Hash32, ChecksumAddress, HexAddress
from hexbytes import HexBytes

ADDRESS_DEFAULT = HexStr("0x" + "0" * 40)
L2_ETH_TOKEN_ADDRESS = HexStr('0x000000000000000000000000000000000000800a')

REQUIRED_L1_TO_L2_GAS_PER_PUBDATA_LIMIT = 800

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
        return self.l1_address.lower() == ADDRESS_DEFAULT or \
            self.l2_address.lower() == L2_ETH_TOKEN_ADDRESS

    def into_decimal(self, amount: int) -> Decimal:
        return Decimal(amount).scaleb(self.decimals) // Decimal(10) ** self.decimals

    def to_int(self, amount: Union[Decimal, int, float]) -> int:
        if isinstance(amount, int) or isinstance(amount, float):
            amount = Decimal(amount)
        return int(amount * (Decimal(10) ** self.decimals))

    @classmethod
    def create_eth(cls) -> 'Token':
        return Token(ADDRESS_DEFAULT, L2_ETH_TOKEN_ADDRESS, "ETH", 18)


@dataclass
class Fee:
    gas_limit: int = 0
    max_fee_per_gas: int = 0
    max_priority_fee_per_gas: int = 0
    gas_per_pubdata_limit: int = 0


@dataclass
class BridgeAddresses:
    erc20_l1_default_bridge: HexStr
    erc20_l2_default_bridge: HexStr


@dataclass
class ZksMessageProof:
    id: int
    proof: List[str]
    root: str


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


class AccountAbstractionVersion(Enum):
    NONE = 0
    VERSION_1 = 1


@dataclass
class Overwrites(dict):
    from_: Optional[ChecksumAddress | HexAddress | HexStr]
    nonce: Optional[int]
    value: Optional[int]
    gas_price: Optional[int]
    gas_limit: Optional[int]
    max_priority_fee_per_gas: Optional[int]
    max_fee_per_gas: Optional[int]


@dataclass
class DepositTransaction(dict):
    token: ChecksumAddress | HexAddress | HexStr
    amount: int
    to: Optional[ChecksumAddress | HexAddress | HexStr]
    operator_tip: Optional[int]
    bridge_address: Optional[ChecksumAddress | HexAddress | HexStr]
    approve_erc20: Optional[bool]
    l2_gas_limit: Optional[int]
    gas_per_pubdata_byte: Optional[int]
    refund_recipient: Optional[ChecksumAddress | HexAddress | HexStr]
    overrides: Optional[Overwrites]
    approve_overrides: Optional[Overwrites]
    custom_bridge_data: Optional[bytes]


@dataclass
class RequestExecuteTransaction(dict):
    contract_address: ChecksumAddress | HexAddress | HexStr
    l2_gas_limit: Optional[int]
    l2_value: Optional[int]
    calldata: Optional[bytes] = None
    factory_deps: Optional[List[bytes]] = None
    operator_tip: Optional[int] = 0
    gas_per_pubdata_byte: Optional[int] = REQUIRED_L1_TO_L2_GAS_PER_PUBDATA_LIMIT
    refund_recipient: Optional[ChecksumAddress | HexAddress | HexStr] = None
    overrides: Optional[Overwrites] = None
