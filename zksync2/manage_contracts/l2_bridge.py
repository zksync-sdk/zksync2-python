import importlib.resources as pkg_resources
from eth_account.signers.base import BaseAccount
from web3 import Web3
from web3.contract import Contract
from eth_typing import HexStr
from typing import Optional
import json

from web3.types import TxReceipt

from zksync2.manage_contracts.gas_provider import GasProvider
from zksync2.manage_contracts import contract_abi

l2_bridge_abi_cache = None


def _l2_bridge_abi_default():
    global l2_bridge_abi_cache

    if l2_bridge_abi_cache is None:
        with pkg_resources.path(contract_abi, "IL2Bridge.json") as p:
            with p.open(mode='r') as json_file:
                data = json.load(json_file)
                l2_bridge_abi_cache = data['abi']
    return l2_bridge_abi_cache


class L2Bridge:
    def __init__(self,
                 contract_address: HexStr,
                 web3_zks: Web3,
                 zksync_account: BaseAccount,
                 gas_provider: GasProvider, abi=None):
        check_sum_address = Web3.toChecksumAddress(contract_address)
        self.web3 = web3_zks
        self.addr = check_sum_address
        self.zksync_account = zksync_account
        self.gas_provider = gas_provider
        if abi is None:
            abi = _l2_bridge_abi_default()
        self.contract: Contract = self.web3.eth.contract(self.addr, abi=abi)

    def _get_nonce(self):
        return self.web3.zksync.get_transaction_count(self.zksync_account.address)

    def finalize_deposit(self,
                         l1_sender: HexStr,
                         l2_receiver: HexStr,
                         l1_token: HexStr,
                         amount: int,
                         data: bytes) -> TxReceipt:
        tx = self.contract.functions.finalizeDeposit(l1_sender,
                                                     l2_receiver,
                                                     l1_token,
                                                     amount,
                                                     data).build_transaction(
            {
                "from": self.zksync_account.address,
                "nonce": self._get_nonce(),
                "gas": self.gas_provider.gas_limit(),
                "gasPrice": self.gas_provider.gas_price()
            })
        signed_tx = self.zksync_account.sign_transaction(tx)
        txn_hash = self.web3.zksync.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.web3.zksync.wait_for_transaction_receipt(txn_hash)
        return txn_receipt

    def l1_bridge(self) -> HexStr:
        return self.contract.functions.l1Bridge().call()

    def l1_token_address(self, l2_token: HexStr):
        return self.contract.functions.l1TokenAddress(l2_token).call()

    def l2_token_address(self, l1_token: HexStr):
        return self.contract.functions.l2TokenAddress(l1_token).call()

    def withdraw(self,
                 l1_receiver: HexStr,
                 l2_token: HexStr,
                 amount: int):
        tx = self.contract.functions.withdraw(l1_receiver,
                                              l2_token,
                                              amount).build_transaction(
            {
                "from": self.zksync_account.address,
                "nonce": self._get_nonce(),
                "gas": self.gas_provider.gas_limit(),
                "gasPrice": self.gas_provider.gas_price()
            })
        signed_tx = self.zksync_account.sign_transaction(tx)
        txn_hash = self.web3.zksync.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.web3.zksync.wait_for_transaction_receipt(txn_hash)
        return txn_receipt


class L2BridgeEncoder:

    def __init__(self, web3: Web3, abi: Optional[dict] = None):
        if abi is None:
            abi = _l2_bridge_abi_default()
        self.contract = web3.eth.contract(address=None, abi=abi)

    def encode_function(self, fn_name: str, args: list) -> HexStr:
        return HexStr(self.contract.encodeABI(fn_name=fn_name, args=args))
