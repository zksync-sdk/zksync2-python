from typing import TypedDict, List, Optional
from eth_typing import HexStr
from web3.types import AccessList

AAParams = TypedDict(
    "AAParams",
    {
        "from": HexStr,
        "signature": bytes
    })

Eip712Meta = TypedDict(
    "Eip712Meta",
    {
        "feeToken": HexStr,
        "ergsPerPubdata": int,
        "ergsPerStorage": int,
        "factoryDeps": Optional[List[bytes]],
        "aaParams": Optional[AAParams]
    })

Transaction = TypedDict(
    "Transaction",
    {
        "from": HexStr,
        "to": HexStr,
        "gas": int,
        "gasPrice": int,
        "value": int,
        "data": HexStr,
        "transactionType": int,
        "accessList": AccessList,
        "eip712Meta": Eip712Meta
    })
