import json
import importlib.resources as pkg_resources
from typing import Optional
from eth_typing import HexStr
from web3 import Web3
from web3.module import Module
# from zksync2.manage_contracts.contract_base import ContractBase
from eth_account.signers.base import BaseAccount
from web3.types import TxReceipt

from zksync2.manage_contracts.gas_provider import GasProvider

from zksync2.manage_contracts import contract_abi

erc_20_abi_cache = None


def _erc_20_abi_default():
    global erc_20_abi_cache

    if erc_20_abi_cache is None:
        with pkg_resources.path(contract_abi, "IERC20.json") as p:
            with p.open(mode='r') as json_file:
                data = json.load(json_file)
                erc_20_abi_cache = data['abi']
    return erc_20_abi_cache


class ERC20Contract:
    MAX_ERC20_APPROVE_AMOUNT = 2 ^ 256 - 1
    ERC20_APPROVE_THRESHOLD = 2 ^ 255

    def __init__(self, web3: Module,
                 contract_address: HexStr,
                 account: BaseAccount,
                 gas_provider: GasProvider):
        check_sum_address = Web3.toChecksumAddress(contract_address)
        self.contract_address = check_sum_address
        self.module = web3
        self.contract = self.module.contract(self.contract_address, abi=_erc_20_abi_default())
        self.account = account
        self.gas_provider = gas_provider

    def _nonce(self) -> int:
        return self.module.get_transaction_count(self.account.address)

    def approve_deposit(self, zksync_address: HexStr, max_erc20_approve_amount=MAX_ERC20_APPROVE_AMOUNT) -> TxReceipt:
        # return self.contract.functions.approve(zksync_address, max_erc20_approve_amount).call()
        tx = self.contract.functions.approve(zksync_address, max_erc20_approve_amount).build_transaction(
            {
                "chainId": self.module.chain_id,
                "from": self.account.address,
                "nonce": self._nonce(),
                "gas": self.gas_provider.gas_limit(),
                "gasPrice": self.gas_provider.gas_price()
            })
        signed_tx = self.account.sign_transaction(tx)
        txn_hash = self.module.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.module.wait_for_transaction_receipt(txn_hash)
        return txn_receipt

    def allowance(self, owner: HexStr, sender: HexStr) -> int:
        return self.contract.functions.allowance(owner, sender).call()

    def transfer(self, _to: str, _value: int) -> TxReceipt:
        tx = self.contract.functions.transfer(_to, _value).build_transaction(
            {
                "from": self.account.address
            }
        )
        signed_tx = self.account.sign_transaction(tx)
        txn_hash = self.module.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.module.wait_for_transaction_receipt(txn_hash)
        return txn_receipt

    def balance_of(self, addr: HexStr):
        return self.contract.functions.balanceOf(addr).call()


class ERC20FunctionEncoder:

    def __init__(self, web3_eth: Web3, abi: Optional[dict] = None):
        if abi is None:
            abi = _erc_20_abi_default()
        self.contract = web3_eth.eth.contract(address=None, abi=abi)

    def encode_method(self, fn_name, args) -> HexStr:
        return self.contract.encodeABI(fn_name=fn_name, args=args)
