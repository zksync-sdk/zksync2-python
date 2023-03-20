import json
import importlib.resources as pkg_resources
from eth_account.signers.base import BaseAccount
from eth_typing import HexStr
from web3 import Web3
from web3.module import Module

from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts import contract_abi

eth_token_abi_cache = None


def _eth_token_abi_default():
    global eth_token_abi_cache

    if eth_token_abi_cache is None:
        with pkg_resources.path(contract_abi, "IEthToken.json") as p:
            with p.open(mode='r') as json_file:
                data = json.load(json_file)
                erc_20_abi_cache = data['abi']
    return erc_20_abi_cache


class EthToken:
    MAX_ERC20_APPROVE_AMOUNT = 2 ^ 256 - 1
    ERC20_APPROVE_THRESHOLD = 2 ^ 255

    def __init__(self, web3: Module,
                 contract_address: HexStr,
                 account: BaseAccount,
                 ):
        check_sum_address = Web3.to_checksum_address(contract_address)
        self.contract_address = check_sum_address
        self.module = web3
        self.contract = self.module.contract(self.contract_address, abi=_eth_token_abi_default())
        self.account = account

    def _nonce(self) -> int:
        return self.module.get_transaction_count(self.account.address, EthBlockParams.LATEST.value)

    def withdraw_tx(self,
                    to: HexStr,
                    amount: int,
                    gas: int,
                    gas_price: int = None):
        if gas_price is None:
            gas_price = self.module.gas_price

        return self.contract.functions.withdraw(to).build_transaction({
            "nonce": self._nonce(),
            "chainId": self.module.chain_id,
            "gas": gas,
            "gasPrice": gas_price,
            "value": amount,
            "from": self.account.address,
        })
