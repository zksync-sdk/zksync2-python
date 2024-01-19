from datetime import datetime
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
        "l2Erc20DefaultBridge": HexStr,
    },
)

ZksContractDebugInfo = TypedDict(
    "ZksContractDebugInfo", {"assemblyCode": HexStr, "pcLineMapping": Dict[int, int]}
)

ZksBlockRange = TypedDict("ZksBlockRange", {"begining": int, "end": int})

ZksBaseSystemContractsHashes = TypedDict(
    "ZksBaseSystemContractsHashes", {"bootloader": str, "defaultAa": str}
)
ZksBatchDetails = TypedDict(
    "ZksBatchDetails",
    {
        "baseSystemContractsHashes": ZksBaseSystemContractsHashes,
        "commitTxHash": str,
        "committedAt": datetime,
        "executeTxHash": str,
        "executedAt": datetime,
        "l1GasPrice": int,
        "l1TxCount": int,
        "l2FairGasPrice": int,
        "l2TxCount": int,
        "number": int,
        "proveTxHash": str,
        "provenAt": datetime,
        "rootHash": str,
        "status": str,
        "timestamp": int,
    },
)

ZksBlockDetails = TypedDict(
    "ZksBlockDetails",
    {
        "commitTxHash": str,
        "committedAt": datetime,
        "executeTxHash": str,
        "executedAt": datetime,
        "l1TxCount": int,
        "l2TxCount": int,
        "number": int,
        "proveTxHash": str,
        "provenAt": datetime,
        "rootHash": str,
        "status": str,
        "timestamp": int,
    },
)

ZksTransactionDetails = TypedDict(
    "ZksTransactionDetails",
    {
        "ethCommitTxHash": str,
        "ethExecuteTxHash": datetime,
        "ethProveTxHash": str,
        "fee": int,
        "initiatorAddress": str,
        "isL1Originated": bool,
        "receivedAt": datetime,
        "status": str,
    },
)

ZksL1ToL2Log = TypedDict(
    "ZksL1ToL2Log",
    {
        "blockHash": HexStr,
        "blockNumber": HexStr,
        "l1BatchNumber": HexStr,
        "transactionIndex": HexStr,
        "transactionHash": HexStr,
        "transactionLogIndex": HexStr,
        "shardId": HexStr,
        "isService": bool,
        "sender": HexStr,
        "key": HexStr,
        "value": HexStr,
        "logIndex": HexStr,
    },
)

ZksTransactionReceipt = TypedDict(
    "ZksTransactionReceipt",
    {
        "from": HexStr,
        "to": HexStr,
        "blockNumber": int,
        "l1BatchTxIndex": HexStr,
        "l2ToL1Logs": List[ZksL1ToL2Log],
    },
)

ZksEstimateFee = NewType("ZksEstimateFee", Fee)
ZksIsTokenLiquid = NewType("ZksIsTokenLiquid", bool)
ZksL1ChainId = NewType("ZksL1ChainId", int)
ZksL1BatchNumber = NewType("ZksL1BatchNumber", int)
ZksMainContract = HexStr
ZksSetContractDebugInfoResult = NewType("ZksSetContractDebugInfoResult", bool)
ZksTokenPrice = NewType("ZksTokenPrice", Decimal)
ZksTokens = NewType("ZksTokens", List[Token])
ZksTransactions = NewType("ZksTransactions", List[TxData])
ZksTransactionTrace = NewType("ZksTransactionTrace", VmDebugTrace)
