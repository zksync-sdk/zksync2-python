import importlib.resources as pkg_resources
import json

from eth_typing import HexStr

from tests import contracts
from eth_utils import remove_0x_prefix


def get_binary(name: str) -> bytes:
    with pkg_resources.path(contracts, name) as p:
        with p.open(mode='rb') as contact_file:
            data = contact_file.read()
            return data


def get_hex_binary(name: str) -> bytes:
    with pkg_resources.path(contracts, name) as p:
        with p.open(mode='r') as contact_file:
            lines = contact_file.readlines()
            data = "".join(lines)
            return bytes.fromhex(remove_0x_prefix(HexStr(data)))


def get_abi(name: str):
    with pkg_resources.path(contracts, name) as p:
        with p.open(mode='r') as json_f:
            return json.load(json_f)
