import json
from typing import Any

from eth_account.signers.base import BaseAccount
from eth_utils import add_0x_prefix, remove_0x_prefix
from web3 import Web3
from pathlib import Path
from eth_typing import HexStr
from web3._utils.abi import get_constructor_abi, merge_args_and_kwargs
from web3._utils.contracts import encode_abi
from web3.types import TxReceipt


def _get_constructor_contract_binary() -> bytes:
    p = Path('./constructor_contract.bin')
    with p.open(mode='rb') as contact_file:
        data = contact_file.read()
        return data


def _get_constructor_contract_abi():
    p = Path('./constructor_contract_abi.json')
    with p.open(mode='r') as json_f:
        return json.load(json_f)


class ConstructorContract:

    def __init__(self, web3: Web3, address: HexStr, abi=None):
        self.web3 = web3
        if abi is None:
            abi = _get_constructor_contract_abi()
        self.contract = self.web3.zksync.contract(address=address, abi=abi)

    def get(self):
        return self.contract.functions.get().call()

    def increment(self, v: int) -> TxReceipt:
        tx_hash = self.contract.functions.increment(v).transact()
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    @classmethod
    def deploy(cls, web3: Web3, account: BaseAccount) -> 'ConstructorContract':
        abi = _get_constructor_contract_abi()
        counter_contract_instance = web3.zksync.contract(abi=abi,
                                                         bytecode=_get_constructor_contract_binary())
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


class ConstructorContractEncoder:

    def __init__(self, web3: Web3):
        self.web3 = web3
        self.abi = _get_constructor_contract_abi()
        self.contract = self.web3.eth.contract(abi=self.abi,
                                               bytecode=_get_constructor_contract_binary())

    def encode_method(self, fn_name, args: list):
        return self.contract.encodeABI(fn_name, args)

    def encode_constructor(self, *args: Any, **kwargs: Any) -> bytes:
        constructor_abi = get_constructor_abi(self.abi)

        if constructor_abi:
            if not args:
                args = tuple()
            if not kwargs:
                kwargs = {}

            arguments = merge_args_and_kwargs(constructor_abi, args, kwargs)
            data = encode_abi(self.web3, constructor_abi, arguments, data=self.contract.bytecode)
            data = bytes.fromhex(remove_0x_prefix(data))
        else:
            # data = to_hex(self.contract.bytecode)
            data = self.contract.bytecode
        return data

    @property
    def bytecode(self) -> bytes:
        return self.contract.bytecode
