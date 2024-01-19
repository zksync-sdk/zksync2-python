import importlib.resources as pkg_resources
import json
from typing import Optional

from web3 import Web3

from zksync2.manage_contracts import contract_abi
from zksync2.manage_contracts.contract_encoder_base import BaseContractEncoder

zksync_abi_cache = None
icontract_deployer_abi_cache = None
paymaster_flow_abi_cache = None
nonce_holder_abi_cache = None
l2_bridge_abi_cache = None
l1_bridge_abi_cache = None
eth_token_abi_cache = None
erc_20_abi_cache = None


def zksync_abi_default():
    global zksync_abi_cache

    if zksync_abi_cache is None:
        with pkg_resources.path(contract_abi, "IZkSync.json") as p:
            with p.open(mode="r") as json_file:
                data = json.load(json_file)
                zksync_abi_cache = data["abi"]
    return zksync_abi_cache


def icontract_deployer_abi_default():
    global icontract_deployer_abi_cache

    if icontract_deployer_abi_cache is None:
        with pkg_resources.path(contract_abi, "ContractDeployer.json") as p:
            with p.open(mode="r") as json_file:
                data = json.load(json_file)
                icontract_deployer_abi_cache = data["abi"]
    return icontract_deployer_abi_cache


def paymaster_flow_abi_default():
    global paymaster_flow_abi_cache

    if paymaster_flow_abi_cache is None:
        with pkg_resources.path(contract_abi, "IPaymasterFlow.json") as p:
            with p.open(mode="r") as json_file:
                data = json.load(json_file)
                paymaster_flow_abi_cache = data["abi"]
    return paymaster_flow_abi_cache


def nonce_holder_abi_default():
    global nonce_holder_abi_cache

    if nonce_holder_abi_cache is None:
        with pkg_resources.path(contract_abi, "INonceHolder.json") as p:
            with p.open(mode="r") as json_file:
                nonce_holder_abi_cache = json.load(json_file)
    return nonce_holder_abi_cache


def l2_bridge_abi_default():
    global l2_bridge_abi_cache

    if l2_bridge_abi_cache is None:
        with pkg_resources.path(contract_abi, "IL2Bridge.json") as p:
            with p.open(mode="r") as json_file:
                data = json.load(json_file)
                l2_bridge_abi_cache = data["abi"]
    return l2_bridge_abi_cache


def l1_bridge_abi_default():
    global l1_bridge_abi_cache

    if l1_bridge_abi_cache is None:
        with pkg_resources.path(contract_abi, "IL1Bridge.json") as p:
            with p.open(mode="r") as json_file:
                data = json.load(json_file)
                l1_bridge_abi_cache = data["abi"]
    return l1_bridge_abi_cache


def eth_token_abi_default():
    global eth_token_abi_cache

    if eth_token_abi_cache is None:
        with pkg_resources.path(contract_abi, "IEthToken.json") as p:
            with p.open(mode="r") as json_file:
                data = json.load(json_file)
                erc_20_abi_cache = data["abi"]
    return erc_20_abi_cache


def get_erc20_abi():
    global erc_20_abi_cache

    if erc_20_abi_cache is None:
        with pkg_resources.path(contract_abi, "IERC20.json") as p:
            with p.open(mode="r") as json_file:
                data = json.load(json_file)
                erc_20_abi_cache = data["abi"]
    return erc_20_abi_cache


class ERC20Encoder(BaseContractEncoder):
    def __init__(self, web3: Web3, abi: Optional[dict] = None):
        if abi is None:
            abi = get_erc20_abi()
        super(ERC20Encoder, self).__init__(web3, abi)
