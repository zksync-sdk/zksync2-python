from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from web3._utils.compat import (
    TypedDict,
)

from eth_typing import HexStr
from web3.types import AccessList
from zksync2.core.types import PaymasterParams


@dataclass
class EIP712Meta:
    ERGS_PER_PUB_DATA_DEFAULT = 16 * 10000

    ergs_per_pub_data: int = ERGS_PER_PUB_DATA_DEFAULT
    custom_signature: Optional[bytes] = None
    factory_deps: Optional[List[bytes]] = None
    paymaster_params: Optional[PaymasterParams] = None


Transaction = TypedDict("Transaction", {
        "chain_id": int,
        "nonce": int,
        "from": HexStr,
        "to": HexStr,
        "gas": int,
        "gasPrice": int,
        "maxPriorityFeePerGas": int,
        "value": int,
        "data": HexStr,
        "transactionType": int,
        "accessList": Optional[AccessList],
        "eip712Meta": EIP712Meta,
}, total=False)


class TransactionType(Enum):
    EIP_712_TX_TYPE = 113
