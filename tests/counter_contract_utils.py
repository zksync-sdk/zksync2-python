import json
from pathlib import Path
from web3 import Web3


def _get_counter_contract_binary() -> bytes:
    p = Path('./counter_contract.hex')
    with p.open(mode='r') as contact_file:
        lines = contact_file.readlines()
        data = "".join(lines)
        return bytes.fromhex(data)


def _get_counter_contract_abi():
    p = Path('./counter_contract_abi.json')
    with p.open(mode='r') as json_f:
        return json.load(json_f)


class CounterContractEncoder:
    def __init__(self, web3: Web3):
        self.counter_contract_instance = web3.eth.contract(abi=_get_counter_contract_abi(),
                                                           bytecode=_get_counter_contract_binary())

    def encode_method(self, fn_name, args: list):
        return self.counter_contract_instance.encodeABI(fn_name, args)
