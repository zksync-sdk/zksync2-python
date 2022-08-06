from typing import Callable

from web3 import Web3
from web3.middleware import Middleware
from web3.types import RPCEndpoint, RPCResponse
from typing import Any
from protocol.zksync_web3.zksync_provider import ZkSyncProvider

ZK_METHODS = [
    "zks_estimateFee",
    "zks_getMainContract",
    "zks_getL1WithdrawalTx",
    "zks_getConfirmedTokens",
    "zks_isTokenLiquid",
    "zks_getTokenPrice",
    "zks_L1ChainId",
    "eth_getBalance",
    "zks_getAllAccountBalances",
    "zks_getBridgeContracts",
    "zks_getL2ToL1MsgProof",
    "eth_gasPrice",
    "eth_estimateGas"
    "zks_setContractDebugInfo",
    "zks_getContractDebugInfo",
    "zks_getTransactionTrace",

]


def build_zksync_middleware(zksync_provider: ZkSyncProvider) -> Middleware:
    def zksync_middleware(make_request: Callable[[RPCEndpoint, Any], Any],
                          w3: Web3) -> Callable[[RPCEndpoint, Any], RPCResponse]:
        def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            return zksync_provider.make_request(method, params)
            # if method not in ZK_METHODS:
            #     return w3.provider.make_request(method, params)
            # else:
            #     return zksync_provider.make_request(method, params)
        return middleware
    return zksync_middleware
