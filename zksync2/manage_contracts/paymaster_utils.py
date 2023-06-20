import importlib.resources as pkg_resources
from web3 import Web3
from eth_typing import HexStr
import json
from zksync2.manage_contracts import contract_abi
from zksync2.manage_contracts.contract_encoder_base import BaseContractEncoder

paymaster_flow_abi_cache = None


def _paymaster_flow_abi_default():
    global paymaster_flow_abi_cache

    if paymaster_flow_abi_cache is None:
        with pkg_resources.path(contract_abi, "IPaymasterFlow.json") as p:
            with p.open(mode='r') as json_file:
                data = json.load(json_file)
                paymaster_flow_abi_cache = data['abi']
    return paymaster_flow_abi_cache


class PaymasterFlowEncoder(BaseContractEncoder):

    def __init__(self, web3: Web3):
        super(PaymasterFlowEncoder, self).__init__(web3, abi=_paymaster_flow_abi_default())

    def encode_approval_based(self, address: HexStr, min_allowance: int, inner_input: bytes) -> HexStr:
        return self.encode_method(fn_name="approvalBased", args=(address, min_allowance, inner_input))

    def encode_general(self, inputs: bytes) -> HexStr:
        return self.encode_method(fn_name="general", args=tuple([inputs]))
