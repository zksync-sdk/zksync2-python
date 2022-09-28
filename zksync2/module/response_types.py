from decimal import Decimal
from typing import TypedDict, NewType, Dict, List
from eth_typing import HexStr
from web3.types import TxData
from zksync2.core.types import Token, VmDebugTrace, Fee

ZksAccountBalances = Dict[str, int]

ZksBridgeAddresses = TypedDict(
    "ZksBridgeAddresses",
    {
        "l1EthDefaultBridge": HexStr,
        "l2EthDefaultBridge": HexStr,
        "l1Erc20DefaultBridge": HexStr,
        "l2Erc20DefaultBridge": HexStr
    })

ZksContractDebugInfo = TypedDict(
    "ZksContractDebugInfo",
    {
        "assemblyCode": HexStr,
        "pcLineMapping": Dict[int, int]
    })

ZksEstimateFee = NewType("ZksEstimateFee", Fee)
ZksIsTokenLiquid = NewType('ZksIsTokenLiquid', bool)
ZksL1ChainId = NewType("ZksL1ChainId", int)
ZksMainContract = HexStr
ZksMessageProof = TypedDict(
    "ZksMessageProof",
    {
        "proof": List[str],
        "id": int,
        "root": str
    })

ZksSetContractDebugInfoResult = NewType("ZksSetContractDebugInfoResult", bool)
ZksTokenPrice = NewType("ZksTokenPrice", Decimal)

ZksTokens = NewType("ZksTokens", List[Token])
ZksTransactions = NewType("ZksTransactions", List[TxData])
ZksTransactionTrace = NewType("ZksTransactionTrace", VmDebugTrace)
