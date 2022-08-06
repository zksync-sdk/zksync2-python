from typing import TypedDict, List, Any
from eth_typing import HexStr

# from typing import cast

Eip712Meta = TypedDict(
    "Eip712Meta",
    {
        "feeToken": HexStr,
        "ergsPerStorage": HexStr,
        "ergsPerPubdata": HexStr,
        "withdrawToken": str,
        "factoryDeps": list
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
        "accessList": List[Any],
        "eip712Meta": Eip712Meta
    })
