from typing import Callable

import web3.eth
from web3 import Web3
from web3.middleware import Middleware
from web3.types import RPCEndpoint, RPCResponse
from typing import Any
from protocol.zksync_provider import ZkSyncProvider

ZK_METHODS = [
    "zks_estimateFee",
    "zks_getMainContract",
    "zks_getL1WithdrawalTx",
    "zks_getAccountTransactions",
    "zks_getConfirmedTokens",
    "zks_isTokenLiquid",
    "zks_getTokenPrice",
    "zks_L1ChainId",
    "eth_getBalance",
    "zks_setContractDebugInfo",
    "zks_getContractDebugInfo",
    "zks_getTransactionTrace",
    "zks_getAllAccountBalances"
]


def build_zksync_middleware(zksync_provider: ZkSyncProvider) -> Middleware:
    def zksync_middleware(make_request: Callable[[RPCEndpoint, Any], Any],
                          w3: Web3) -> Callable[[RPCEndpoint, Any], RPCResponse]:
        def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            if method not in ZK_METHODS:
                return w3.provider.make_request(method, params)
            else:
                return zksync_provider.make_request(method, params)
        return middleware
    return zksync_middleware
