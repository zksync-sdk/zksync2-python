from zksync2.module.zksync_module import ZkSync
from zksync2.module.zksync_provider import ZkSyncProvider
from zksync2.module.middleware import build_zksync_middleware

from typing import Union
from eth_typing import URI
from web3 import Web3


class ZkWeb3(Web3):
    zksync: ZkSync


class ZkSyncBuilder:
    @classmethod
    def build(cls, url: Union[URI, str]) -> ZkWeb3:
        web3_module = Web3()
        zksync_provider = ZkSyncProvider(url)
        zksync_middleware = build_zksync_middleware(zksync_provider)
        web3_module.middleware_onion.add(zksync_middleware)
        web3_module.zksync = ZkSync(web3_module)
        return web3_module
