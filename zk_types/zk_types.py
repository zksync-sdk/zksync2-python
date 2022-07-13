from dataclasses import dataclass, field
from hexbytes import HexBytes
from web3.types import Hash32, HexStr, Nonce, Wei
from typing import TypedDict, Union, NewType, Dict, Optional
from eth_typing import Address, HexAddress, BlockNumber
from decimal import Decimal

# TODO: add builders and types with convertors

# INFO: see original
# public class Eip712Meta {
#     private String feeToken;
#     private BigInteger ergsPerStorage;
#     private BigInteger ergsPerPubdata;
#     private String withdrawToken;
#     private byte[][] factoryDeps;

# TODO: type depends fields - > DO POLYMORPHYC TYPE
Eip712Meta = TypedDict(
    "Eip712Meta",
    {
        "feeToken": HexStr,
        "ergsPerStorage": HexStr,
        "ergsPerPubdata": HexStr,
        "withdrawToken": str,
        "factoryDeps": list
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

# EstimateFeeResult = TypedDict(
#     "EstimateFee",
#     {
#         "feeToken": TokenAddress,
#         "ergsLimit": HexBytes,
#         "ergsPriceLimit": HexBytes,
#         "ergsPerStorageLimit": HexBytes,
#         "ergsPerPubdataLimit": HexBytes
#     })

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
    # TODO: make JSON serializable
    # TODO: MOVE TO EIP712 serializable !!!
    name: str
    version: str
    chainId: HexBytes
    verifyingContract: Address


@dataclass
class Fee:
    feeToken: TokenAddress
    ergsLimit: HexBytes
    ergsPriceLimit: HexBytes
    ergsPerStorageLimit: HexBytes
    ergsPerPubdataLimit: HexBytes
    # ergsLimit: HexBytes = HexBytes(0)
    # ergsPriceLimit: HexBytes = HexBytes(0)
    # ergsPerStorageLimit: HexBytes = HexBytes(0)
    # ergsPerPubdataLimit: HexBytes = HexBytes(0)


@dataclass
class Token:
    address: TokenAddress
    symbol: str
    decimals: int

    # ETH_TOKEN: Token = field(default_factory=self.create_eth)

    # ETH_TOKEN = self.create_eth()

    @staticmethod
    def create_eth():
        addr = TokenAddress(HexStr("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"))
        return Token(address=addr, symbol="ETH", decimals=18)

    def is_eth(self) -> bool:
        _ETH = HexStr("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        return self.address == _ETH and self.symbol == "ETH"

    def into_decimals(self, amount: int) -> Decimal:
        # return Decimal(amount).scaleb(-self.decimals)
        x = Decimal(amount).scaleb(self.decimals)
        d = Decimal(10) ** self.decimals
        # INFO: might need round down
        return x / d

    # def from_decimal(self, amount: Decimal) -> int:
    #     return int(amount.scaleb(self.decimals))

    # INFO: WEI TO ETH
    # ONLY FOR ZKSYNC
    def to_int(self, amount: Decimal) -> int:
        # return int(amount.scaleb(self.decimals))
        return int(amount * (Decimal(10) ** self.decimals))


@dataclass
class Transfer:
    to: Address
    amount: Decimal
    token: Optional[Token] = None
    nonce: Optional[int] = None


@dataclass
class Withdraw:
    to: Address
    amount: Decimal
    token: Optional[Token] = None
    nonce: Optional[int] = None
