from dataclasses import dataclass
from hexbytes import HexBytes
from web3.types import Hash32, HexStr, Nonce, Wei
from typing import TypedDict, Union, NewType, Dict
from eth_typing import Address, HexAddress, BlockNumber
from decimal import Decimal

# class EIP712Meta(TypedDict):
#     feeToken: str,
#     ergsPerStorage: int


# TODO: add builders and types with convertors

Eip712Meta = TypedDict(
    "Eip712Meta",
    {
        "feeToken": HexStr,
        "ergsPerStorage": HexStr,
        "ergsPerPubdata": HexStr
    })

# INFO: ONLY FOR estimationFee as Input Type
Transaction = TypedDict(
    "Transaction",
    {
        "from": HexStr,
        "to": HexStr,
        "gas": HexStr,
        "gasPrice": HexStr,
        "value": HexStr,
        "data": HexStr,
        "transactionType": HexStr,
        "eip712Meta": Eip712Meta
    })

# INFO: can't find correct type under Eth
TransactionInfo = TypedDict(
    "TransactionInfo",
    {
        "blockHash": HexStr,
        "blockNumber": BlockNumber,
        "from": HexAddress,
        "gas": Wei,
        "gasPrice": Wei,
        "hash": Hash32,
        "input": HexStr,
        "nonce": Nonce,
        "to": HexAddress,
        "transactionIndex": int,
        "value": Wei
    })

TransactionHash = Union[Hash32, HexBytes, HexStr]
L1WithdrawHash = Union[Hash32, HexBytes, HexStr]
Before = NewType('offset', int)
Limit = NewType('limit', int)
TokenAddress = NewType('token_address', HexStr)

EstimateFeeResult = TypedDict(
    "EstimateFee",
    {
        "feeToken": TokenAddress,
        "ergsLimit": HexBytes,
        "ergsPriceLimit": HexBytes,
        "ergsPerStorageLimit": HexBytes,
        "ergsPerPubdataLimit": HexBytes
    })

TokenDescription = TypedDict(
    "TokenDescription",
    {
      "name": str,
      "symbol": str,
      "decimals": int,
      "address": Address
    })

TokenPriceUSD = NewType('priceUSD', Decimal)
ContractAddress = HexAddress


class ContractDebugInfo(TypedDict):
    assemblyCode: str
    pcLineMapping: Dict[int, int]


@dataclass
class Eip712Domain:
    name: str
    version: str
    chainId: HexBytes
    verifyingContract: Address
