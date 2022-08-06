import logging
from typing import Union, Optional, Any
from web3 import HTTPProvider
from eth_typing import URI
from web3.types import RPCEndpoint, RPCResponse


class ZkSyncProvider(HTTPProvider):
    logger = logging.getLogger("ZkSyncProvider")

    def __init__(self, url: Optional[Union[URI, str]]):
        super(ZkSyncProvider, self).__init__(url, request_kwargs={'timeout': 1000})

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        self.logger.debug(f"make_request: {method}, params : {params}")
        response = HTTPProvider.make_request(self, method, params)
        return response
