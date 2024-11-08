import itertools
import json
from enum import Enum
from pathlib import Path
from typing import Any, Optional, cast, Tuple
from eth_typing import HexStr
from eth_utils import remove_0x_prefix
from web3 import Web3
from web3._utils.contracts import encode_abi


class JsonConfiguration(Enum):
    COMBINED = "combined"
    STANDARD = "standard"


class BaseContractEncoder:
    @classmethod
    def from_json(
        cls,
        web3: Web3,
        compiled_contract: Path,
        conf_type: JsonConfiguration = JsonConfiguration.COMBINED,
    ):
        with compiled_contract.open(mode="r") as json_f:
            data = json.load(json_f)
            if conf_type == JsonConfiguration.COMBINED:
                contracts = list()
                for contract_path, contract_data in data["contracts"].items():
                    # Check if 'abi' key exists
                    if "abi" in contract_data and "bin" in contract_data:
                        abi = contract_data["abi"]
                        bin = contract_data["bin"]
                        contracts.append(cls(web3, abi=abi, bytecode=bin))

                return contracts
            else:
                return cls(web3, abi=data["abi"], bytecode=data["bytecode"])

    def __init__(self, web3: Web3, abi, bytecode: Optional[bytes] = None):
        self.web3 = web3
        self.abi = abi
        if bytecode is None:
            self.instance_contract = self.web3.eth.contract(abi=self.abi)
        else:
            self.instance_contract = self.web3.eth.contract(
                abi=self.abi, bytecode=bytecode
            )

    def encode_method(self, fn_name, args: tuple) -> HexStr:
        return self.instance_contract.encode_abi(fn_name, args)

    @property
    def contract(self):
        return self.instance_contract


class ContractEncoder(BaseContractEncoder):
    def __init__(self, web3: Web3, abi, bytecode=None):
        super(ContractEncoder, self).__init__(web3, abi, bytecode)

    def encode_constructor(self, *args: Any, **kwargs: Any) -> bytes:
        contract = self.web3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        constructor_abi = get_constructor_abi(contract.abi)

        if constructor_abi:
            if not args:
                args = tuple()
            if not kwargs:
                kwargs = {}
            arguments = merge_args_and_kwargs(constructor_abi["inputs"], args, kwargs)
            # INFO: it takes affect on the eth_estimate_gas,
            #       it does not need the bytecode in the front of encoded arguments, see implementation of encode_abi
            #  uncomment if it's fixed on ZkSync side
            # data = encode_abi(self.web3, constructor_abi, arguments, data=self.instance_contract.bytecode)
            data = encode_abi(self.web3, constructor_abi, arguments)
            data = bytes.fromhex(remove_0x_prefix(data))
        else:
            data = self.instance_contract.bytecode
        return data

    @property
    def bytecode(self):
        return self.instance_contract.bytecode


def merge_args_and_kwargs(abi_inputs, args, kwargs):
    if len(args) + len(kwargs) != len(abi_inputs):
        raise TypeError(
            f"Incorrect argument count. Expected '{len(abi_inputs)}'"
            f". Got '{len(args) + len(kwargs)}'"
        )

    # If no keyword args were given, we don't need to align them
    if not kwargs:
        return cast(Tuple[Any, ...], args)

    kwarg_names = set(kwargs.keys())
    sorted_arg_names = tuple(arg_abi["name"] for arg_abi in abi_inputs)
    args_as_kwargs = dict(zip(sorted_arg_names, args))

    # Check for duplicate args
    duplicate_args = kwarg_names.intersection(args_as_kwargs.keys())
    if duplicate_args:
        raise TypeError(
            f"{abi_inputs.get('name')}() got multiple values for argument(s) "
            f"'{', '.join(duplicate_args)}'"
        )

    # Check for unknown args
    unknown_args = kwarg_names.difference(sorted_arg_names)
    if unknown_args:
        if abi_inputs.get("name"):
            raise TypeError(
                f"{abi_inputs.get('name')}() got unexpected keyword argument(s)"
                f" '{', '.join(unknown_args)}'"
            )
        raise TypeError(
            f"Type: '{abi_inputs.get('type')}' got unexpected keyword argument(s)"
            f" '{', '.join(unknown_args)}'"
        )

    # Sort args according to their position in the ABI and unzip them from their
    # names
    sorted_args = tuple(
        zip(
            *sorted(
                itertools.chain(kwargs.items(), args_as_kwargs.items()),
                key=lambda kv: sorted_arg_names.index(kv[0]),
            )
        )
    )

    if sorted_args:
        return sorted_args[1]
    else:
        return tuple()


def get_constructor_abi(contract_abi):
    for item in contract_abi:
        if item.get("type") == "constructor":
            return item
    return None
