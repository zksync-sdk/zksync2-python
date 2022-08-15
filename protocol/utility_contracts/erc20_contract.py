import importlib.resources as pkg_resources
from eth_typing import HexStr
from web3 import Web3

from protocol.contract_base import ContractBase
from eth_account.signers.base import BaseAccount
import json
from .. import contract_abi

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
        # return self._call_method('approve', self.zksync_address, max_erc20_approve_amount)
        # return self.contract.functions.approve(self.zksync_address, max_erc20_approve_amount).transaction(
        # {"from": self.account.address})
        return self.contract.functions.approve(zksync_address, max_erc20_approve_amount).transaction(
            {"from": self.account.address})

    # def is_deposit_approved(self, erc20_approve_threshold=ERC20_APPROVE_THRESHOLD):
    #     allowance = self.contract.functions.allowance(self.account.address,
    #                                                   self.zksync_address).call()
    #     return allowance >= erc20_approve_threshold
    def is_deposit_approved(self, zksync_address: HexStr, to: str, erc20_approve_threshold=ERC20_APPROVE_THRESHOLD):
        # allowance = self.contract.functions.allowance(to,
        #                                               self.zksync_address).call()
        allowance = self.contract.functions.allowance(to, zksync_address).call()
        return allowance >= erc20_approve_threshold

    def transfer(self, _to: str, _value: int):
        # self._call_method("transfer", _to, _value)
        self.contract.functions.transfer(_to, _value).transaction({"from": self.account.address})
