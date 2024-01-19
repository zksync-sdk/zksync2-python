from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Union, NewType, Dict, List, Any

from eth_typing import HexStr, Hash32
from hexbytes import HexBytes
from web3.contract import Contract
from web3.types import AccessList

from zksync2.core.utils import DEPOSIT_GAS_PER_PUBDATA_LIMIT


class RecommendedGasLimit(IntEnum):
    DEPOSIT = 10000000
    EXECUTE = 620000
    ERC20_APPROVE = 50000
    DEPOSIT_GAS_PER_PUBDATA_LIMIT = 800

ADDRESS_DEFAULT = HexStr("0x" + "0" * 40)
L2_ETH_TOKEN_ADDRESS = HexStr("0x000000000000000000000000000000000000800a")

TokenAddress = NewType("token_address", HexStr)
TransactionHash = Union[Hash32, HexBytes, HexStr]
L2WithdrawTxHash = Union[Hash32, HexBytes, HexStr]
From = NewType("from", int)
Limit = NewType("limit", int)


class ZkBlockParams(Enum):
    COMMITTED = "committed"
    FINALIZED = "finalized"
    PENDING = "pending"
    LATEST = "latest"
    EARLIEST = "earliest"


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
        return (
            self.l1_address.lower() == ADDRESS_DEFAULT
            or self.l2_address.lower() == L2_ETH_TOKEN_ADDRESS
        )

    def into_decimal(self, amount: int) -> Decimal:
        return Decimal(amount).scaleb(self.decimals) // Decimal(10) ** self.decimals

    def to_int(self, amount: Union[Decimal, int, float]) -> int:
        if isinstance(amount, int) or isinstance(amount, float):
            amount = Decimal(amount)
        return int(amount * (Decimal(10) ** self.decimals))

    @classmethod
    def create_eth(cls) -> "Token":
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
    weth_bridge_l1: HexStr
    weth_bridge_l2: HexStr

@dataclass
class L1BridgeContracts:
    erc20: Contract
    weth: Contract

@dataclass
class L2BridgeContracts:
    erc20: Contract
    weth: Contract


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


class AccountNonceOrdering(Enum):
    Sequential = 0
    Arbitrary = 1


@dataclass
class ContractAccountInfo:
    account_abstraction_version: AccountAbstractionVersion
    account_nonce_ordering: AccountNonceOrdering

@dataclass
class BlockRange:
    beginning: str
    end: str


@dataclass
class BaseSystemContractsHashes:
    bootloader: str
    default_aa: str


@dataclass
class BatchDetails:
    base_system_contracts_hashes: BaseSystemContractsHashes
    commit_tx_hash: str
    committed_at: datetime
    execute_tx_hash: str
    executed_at: datetime
    l1_gas_price: int
    l1_tx_count: int
    l2_fair_gas_price: int
    l2_tx_count: int
    number: int
    prove_tx_hash: str
    proven_at: datetime
    root_hash: str
    status: str
    timestamp: int


@dataclass
class BlockDetails:
    commit_tx_hash: str
    committed_at: datetime
    execute_tx_hash: str
    executed_at: datetime
    l1_tx_count: int
    l2_tx_count: int
    number: int
    prove_tx_hash: str
    proven_at: datetime
    root_hash: str
    status: str
    timestamp: int


@dataclass
class TransactionDetails:
    ethCommitTxHash: str
    ethExecuteTxHash: datetime
    ethProveTxHash: str
    fee: int
    initiatorAddress: str
    isL1Originated: bool
    receivedAt: datetime
    status: str


@dataclass
class TransactionOptions:
    chain_id: int = None
    nonce: int = None
    value: int = None
    gas_price: int = None
    max_fee_per_gas: int = None
    max_priority_fee_per_gas: int = None
    gas_limit: int = None


@dataclass
class WithdrawTransaction:
    token: HexStr
    amount: int
    to: HexStr = None
    bridge_address: HexStr = None
    options: TransactionOptions = None


@dataclass
class DepositTransaction:
    token: HexStr
    amount: int = None
    to: HexStr = None
    operator_tip: int = 0
    bridge_address: HexStr = None
    approve_erc20: bool = False
    l2_gas_limit: int = None
    gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT
    custom_bridge_data: bytes = None
    refund_recipient: HexStr = None
    l2_value: int = 0
    options: TransactionOptions = None


@dataclass
class TransferTransaction:
    to: HexStr
    amount: int = 0
    token_address: HexStr = None
    gas_per_pub_data: int = 50000
    options: TransactionOptions = None


@dataclass
class RequestExecuteCallMsg:
    contract_address: HexStr
    call_data: Union[bytes, HexStr]
    from_: HexStr = None
    l2_gas_limit: int = 0
    l2_value: int = 0
    factory_deps: List[bytes] = None
    operator_tip: int = 0
    gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT
    refund_recipient: HexStr = None
    options: TransactionOptions = None


@dataclass
class L1ToL2Log:
    block_hash: HexStr
    block_number: HexStr
    l1_batch_number: HexStr
    transaction_index: HexStr
    transaction_hash: HexStr
    transaction_log_index: HexStr
    shard_id: HexStr
    is_service: bool
    sender: HexStr
    key: HexStr
    value: HexStr
    log_index: HexStr


@dataclass
class TransactionReceipt:
    from_: HexStr
    to: HexStr
    block_number: int
    l1_batch_tx_index: HexStr
    l2_to_l1_logs: List[L1ToL2Log]


@dataclass
class FullDepositFee:
    base_cost: int
    l1_gas_limit: int
    l2_gas_limit: int
    max_fee_per_gas: int = None
    max_priority_fee_per_gas: int = None
    gas_price: int = None







