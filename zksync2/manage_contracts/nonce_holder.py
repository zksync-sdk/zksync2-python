import importlib.resources as pkg_resources
from eth_account.signers.base import BaseAccount
from web3 import Web3
from eth_typing import HexStr
import json

from web3.types import Nonce

from .deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts import contract_abi

nonce_holder_abi_cache = None


def _nonce_holder_abi_default():
    global nonce_holder_abi_cache

    if nonce_holder_abi_cache is None:
        with pkg_resources.path(contract_abi, "INonceHolder.json") as p:
            with p.open(mode='r') as json_file:
                nonce_holder_abi_cache = json.load(json_file)
    return nonce_holder_abi_cache


class NonceHolder:

    def __init__(self,
                 zksync: Web3,
                 account: BaseAccount):
        self.web3 = zksync
        self.account = account
        self.contract = self.web3.zksync.contract(address=ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value,
                                                  abi=_nonce_holder_abi_default())

    def get_account_nonce(self) -> Nonce:
        return self.contract.functions.getAccountNonce().call()

    def get_deployment_nonce(self, addr: HexStr) -> Nonce:
        return self.contract.functions.getDeploymentNonce(addr).call()

    def get_raw_nonce(self, addr: HexStr) -> Nonce:
        return self.contract.functions.getRawNonce(addr).call()

    def increment_deployment_nonce(self, addr: HexStr):
        return self.contract.functions.incrementDeploymentNonce(addr).call()

    def increment_nonce(self):
        return self.contract.functions.incrementNonce().call()

    def increment_nonce_if_equals(self, expected_nonce: Nonce):
        return self.contract.functions.incrementNonceIfEquals(expected_nonce).call()

