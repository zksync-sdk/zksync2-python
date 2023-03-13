import importlib.resources as pkg_resources
from tests import contracts


def contract_path(contract_name: str):
    return pkg_resources.path(contracts, contract_name)
