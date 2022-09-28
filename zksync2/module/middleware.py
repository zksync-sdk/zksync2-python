from typing import Callable

from web3 import Web3
from web3.middleware import Middleware
from web3.types import RPCEndpoint, RPCResponse
from typing import Any
from zksync2.module.zksync_provider import ZkSyncProvider


def build_zksync_middleware(zksync_provider: ZkSyncProvider) -> Middleware:
    def zksync_middleware(make_request: Callable[[RPCEndpoint, Any], Any],
                          w3: Web3) -> Callable[[RPCEndpoint, Any], RPCResponse]:
        def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            return zksync_provider.make_request(method, params)
        return middleware
    return zksync_middleware
