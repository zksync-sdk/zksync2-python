from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Union, NewType, Dict, List, Any, Optional

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
ETH_ADDRESS_IN_CONTRACTS = HexStr("0x0000000000000000000000000000000000000001")
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
    name: str
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
        return Token(ADDRESS_DEFAULT, L2_ETH_TOKEN_ADDRESS, "Ether", "ETH", 18)


@dataclass
class Fee:
    gas_limit: int = 0
    max_fee_per_gas: int = 0
    max_priority_fee_per_gas: int = 0
    gas_per_pubdata_limit: int = 0


@dataclass
class BridgeAddresses:
    erc20_l1_default_bridge: HexStr
    shared_l1_default_bridge: HexStr
    shared_l2_default_bridge: HexStr
    erc20_l2_default_bridge: HexStr
    weth_bridge_l1: HexStr
    weth_bridge_l2: HexStr


@dataclass
class L1BridgeContracts:
    erc20: Contract
    shared: Contract
    weth: Contract


@dataclass
class L2BridgeContracts:
    erc20: Contract
    weth: Contract
    shared: Contract


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
    paymaster_params: PaymasterParams = None


@dataclass
class DepositTransaction:
    token: HexStr
    amount: int = None
    to: HexStr = None
    operator_tip: int = 0
    bridge_address: HexStr = None
    approve_erc20: bool = False
    approve_base_erc20: bool = False
    l2_gas_limit: int = None
    gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT
    custom_bridge_data: bytes = None
    refund_recipient: HexStr = None
    l2_value: int = 0
    options: TransactionOptions = None
    approve_options: TransactionOptions = None
    approve_base_options: TransactionOptions = None


@dataclass
class TransferTransaction:
    to: HexStr
    amount: int = 0
    token_address: HexStr = None
    gas_per_pub_data: int = 50000
    paymaster_params: PaymasterParams = None
    options: TransactionOptions = None


@dataclass
class PaymasterParams:
    paymaster: HexStr
    paymaster_input: bytes


@dataclass
class RequestExecuteCallMsg:
    contract_address: HexStr
    call_data: Union[bytes, HexStr]
    from_: HexStr = None
    l2_gas_limit: int = 0
    mint_value: int = 0
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
    transaction_index_in_l1_batch: HexStr = None


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


@dataclass
class StorageProofData:
    key: HexStr
    value: HexStr
    index: int
    proof: List[HexStr]


@dataclass
class StorageProof:
    address: HexStr
    storageProof: StorageProofData


@dataclass
class VerificationKeysHashesParams:
    recursion_node_level_vk_hash: str
    recursion_leaf_level_vk_hash: str
    recursion_circuits_set_vks_hash: str


@dataclass
class VerificationKeysHashes:
    params: VerificationKeysHashesParams
    recursion_scheduler_level_vk_hash: str


@dataclass
class BaseSystemContracts:
    bootloader: str
    default_aa: str


@dataclass
class ProtocolVersion:
    """Represents the protocol version."""

    version_id: int  # Protocol version ID.
    timestamp: int  # Unix timestamp of the version's activation.
    verification_keys_hashes: VerificationKeysHashes  # Contains the hashes of various verification keys used in the protocol.
    base_system_contracts: (
        BaseSystemContracts  # Addresses of the base system contracts.
    )
    l2_system_upgrade_tx_hash: HexStr = (
        None  # Hash of the transaction used for the system upgrade, if any.
    )


@dataclass
class StorageLog:
    address: str
    key: str
    writtenValue: str


@dataclass
class Event:
    address: str
    topics: List[str]
    data: str
    blockHash: Optional[str]
    blockNumber: Optional[int]
    l1BatchNumber: Optional[int]
    transactionHash: str
    transactionIndex: int
    logIndex: Optional[int]
    transactionLogIndex: Optional[int]
    logType: Optional[str]
    removed: bool


@dataclass
class TransactionWithDetailedOutput:
    """Represents the transaction with detailed output."""

    transactionHash: str  # Transaction hash.
    storageLogs: List[StorageLog]  # Storage slots.
    events: List[Event]  # Generated events.


@dataclass
class Config:
    minimal_l2_gas_price: int  # Minimal gas price on L2.
    compute_overhead_part: int  # Compute overhead part in fee calculation.
    pubdata_overhead_part: int  # Public data overhead part in fee calculation.
    batch_overhead_l1_gas: int  # Overhead in L1 gas for a batch of transactions.
    max_gas_per_batch: int  # Maximum gas allowed per batch.
    max_pubdata_per_batch: int  # Maximum amount of public data allowed per batch.


@dataclass
class V2:
    config: Config  # Settings related to transaction fee computation.
    l1_gas_price: int  # Current L1 gas price.
    l1_pubdata_price: int  # Price of storing public data on L1.


@dataclass
class FeeParams:
    """Represents the fee parameters configuration."""

    V2: V2  # Fee parameter configuration for the current version of the ZKsync protocol.
