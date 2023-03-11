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
    # GAS_PER_PUB_DATA_DEFAULT = 16 * 10000
    # GAS_PER_PUB_DATA_DEFAULT = 20 * 10000
    GAS_PER_PUB_DATA_DEFAULT = 50000

    gas_per_pub_data: int = GAS_PER_PUB_DATA_DEFAULT
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
