import json
import importlib.resources as pkg_resources
from typing import Optional
from eth_typing import HexStr
from web3 import Web3
from zksync2.manage_contracts.contract_base import ContractBase
from eth_account.signers.base import BaseAccount
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


class ERC20Contract(ContractBase):

    MAX_ERC20_APPROVE_AMOUNT = 2 ^ 256 - 1
    ERC20_APPROVE_THRESHOLD = 2 ^ 255

    def __init__(self, web3: Web3, contract_address: HexStr, account: BaseAccount):
        super(ERC20Contract, self).__init__(contract_address, web3, account, _erc_20_abi_default())

    def approve_deposit(self, zksync_address: HexStr, max_erc20_approve_amount=MAX_ERC20_APPROVE_AMOUNT):
        return self.contract.functions.approve(zksync_address, max_erc20_approve_amount).transaction(
            {"from": self.account.address})

    def allowance(self, owner: HexStr, sender: HexStr) -> int:
        return self.contract.functions.allowance(owner, sender).call()

    def transfer(self, _to: str, _value: int):
        self.contract.functions.transfer(_to, _value).transaction({"from": self.account.address})


class ERC20FunctionEncoder:

    def __init__(self, web3_eth: Web3, abi: Optional[dict] = None):
        if abi is None:
            abi = _erc_20_abi_default()
        self.contract = web3_eth.eth.contract(address=None, abi=abi)

    def encode_method(self, fn_name, args) -> HexStr:
        return self.contract.encodeABI(fn_name=fn_name, args=args)
