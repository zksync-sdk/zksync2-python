import json
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from eth_typing import HexStr
from eth_utils import remove_0x_prefix
from web3 import Web3
from web3._utils.abi import get_constructor_abi, merge_args_and_kwargs
from web3._utils.contracts import encode_abi


class JsonConfiguration(Enum):
    COMBINED = "combined"
    STANDARD = "standard"


class BaseContractEncoder:

    @classmethod
    def from_json(cls, web3: Web3, compiled_contract: Path, conf_type: JsonConfiguration = JsonConfiguration.COMBINED):
        with compiled_contract.open(mode='r') as json_f:
            data = json.load(json_f)
            if conf_type == JsonConfiguration.COMBINED:
                return [cls(web3, abi=v["abi"], bytecode=v["bin"]) for k, v in data["contracts"].items()]
            else:
                return cls(web3, abi=data["abi"], bytecode=data["bytecode"])

    def __init__(self, web3: Web3, abi, bytecode: Optional[bytes] = None):
        self.web3 = web3
        self.abi = abi
        if bytecode is None:
            self.instance_contract = self.web3.eth.contract(abi=self.abi)
        else:
            self.instance_contract = self.web3.eth.contract(abi=self.abi, bytecode=bytecode)

    def encode_method(self, fn_name, args: tuple) -> HexStr:
        return self.instance_contract.encodeABI(fn_name, args)

    @property
    def contract(self):
        return self.instance_contract


class ContractEncoder(BaseContractEncoder):

    def __init__(self, web3: Web3, abi, bytecode):
        super(ContractEncoder, self).__init__(web3, abi, bytecode)

    def encode_constructor(self, *args: Any, **kwargs: Any) -> bytes:
        constructor_abi = get_constructor_abi(self.abi)

        if constructor_abi:
            if not args:
                args = tuple()
            if not kwargs:
                kwargs = {}
            arguments = merge_args_and_kwargs(constructor_abi, args, kwargs)
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
