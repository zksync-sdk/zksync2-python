import json
from eth_account.signers.base import BaseAccount
from web3 import Web3
from pathlib import Path
from eth_typing import HexStr
from web3.types import TxReceipt


def _get_custom_account_binary() -> bytes:
    p = Path('./custom_account.bin')
    with p.open(mode='rb') as contact_file:
        data = contact_file.read()
        return data


def _get_custom_account_abi():
    p = Path('./custom_account_abi.json')
    with p.open(mode='r') as json_f:
        return json.load(json_f)


class CustomAccountContract:

    def __init__(self, web3: Web3, address: HexStr, abi=None):
        self.web3 = web3
        if abi is None:
            abi = _get_custom_account_abi()
        self.contract = self.web3.zksync.contract(address=address, abi=abi)

    def get(self):
        return self.contract.functions.get().call()

    def increment(self, v: int) -> TxReceipt:
        tx_hash = self.contract.functions.increment(v).transact()
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    @classmethod
    def deploy(cls, web3: Web3, account: BaseAccount) -> 'CustomAccountContract':
        abi = _get_custom_account_abi()
        counter_contract_instance = web3.zksync.contract(abi=abi,
                                                         bytecode=_get_custom_account_binary())
        tx_hash = counter_contract_instance.constructor().transact(
            {
                "from": account.address,
            }
        )
        tx_receipt = web3.zksync.wait_for_transaction_receipt(tx_hash)
        return cls(web3, tx_receipt["contractAddress"], abi)

    @property
    def address(self):
        return self.contract.address


class CustomAccountEncoder:

    def __init__(self, web3: Web3):
        self.web3 = web3
        self.counter_contract = self.web3.eth.contract(abi=_get_custom_account_abi(),
                                                       bytecode=_get_custom_account_binary())

    def encode_method(self, fn_name, args: list):
        return self.counter_contract.encodeABI(fn_name, args)
