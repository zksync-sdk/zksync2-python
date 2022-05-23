from eth_typing import HexStr
from hexbytes import HexBytes
from typing import TypedDict, Union, NewType, Dict
from web3.types import Hash32

# from eth_typing import Address, BlockIdentifier, Con

# class EIP712Meta(TypedDict):
#     feeToken: str,
#     ergsPerStorage: int

Eip712Meta = TypedDict(
    "Eip712Meta",
    {
        "feeToken": str,
        "ergsPerStorage": int,
        "ergsPerPubdata": int
    })

Transaction = TypedDict(
    "Transaction",
    {
        "from": HexStr,
        "to": HexStr,
        "gas": HexStr,
        "gasPrice": HexStr,
        "value": HexStr,
        "data": HexStr,
        "transactionType": int,
        "eip712Meta": Eip712Meta
    })

L1WithdrawHash = Union[Hash32, HexBytes, HexStr]

# Address = NewType('address', HexStr)
Before = NewType('offset', int)
Limit = NewType('limit', int)
TokenAddress = NewType('tokenAddress', bytes)


class ContractDebugInfo(TypedDict):
    assemblyCode: str
    pcLineMapping: Dict[int, int]
