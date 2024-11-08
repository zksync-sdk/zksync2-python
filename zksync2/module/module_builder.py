from typing import Union

from eth_typing import URI
from web3 import Web3
from web3._utils.module import attach_modules

from zksync2.module.zksync_module import ZkSync
from zksync2.module.zksync_provider import ZkSyncProvider


class ZkWeb3(Web3):
    zksync: ZkSync

    def __init__(self, provider):
        super().__init__(provider)
        # Attach the zksync module
        attach_modules(self, {"zksync": (ZkSync,)})


class ZkSyncBuilder:
    @classmethod
    def build(cls, url: Union[URI, str]) -> ZkWeb3:
        zksync_provider = ZkSyncProvider(url)
        web3_module = ZkWeb3(zksync_provider)
        return web3_module
