from typing import Any
from eth_account.signers.base import BaseAccount
from eth_utils import remove_0x_prefix
from web3 import Web3
from eth_typing import HexStr
from web3._utils.abi import get_constructor_abi, merge_args_and_kwargs
from web3._utils.contracts import encode_abi
from web3.types import TxReceipt
from tests.contracts.utils import get_abi, get_hex_binary


class ConstructorContract:

    def __init__(self, web3: Web3, address: HexStr, abi=None):
        self.web3 = web3
        if abi is None:
            abi = get_abi("constructor_contract_abi.json")
        self.contract = self.web3.zksync.contract(address=address, abi=abi)

    def get(self):
        return self.contract.functions.get().call()

    def increment(self, v: int) -> TxReceipt:
        tx_hash = self.contract.functions.increment(v).transact()
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    @classmethod
    def deploy(cls, web3: Web3, account: BaseAccount) -> 'ConstructorContract':
        abi = get_abi("constructor_contract_abi.json")
        counter_contract_instance = web3.zksync.contract(abi=abi,
                                                         bytecode=get_hex_binary("constructor_contract.hex"))
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
        self.abi = get_abi("constructor_contract_abi.json")
        self.contract = self.web3.eth.contract(abi=self.abi,
                                               bytecode=get_hex_binary("constructor_contract.hex"))

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
            data = self.contract.bytecode
        return data

    @property
    def bytecode(self) -> bytes:
        return self.contract.bytecode
