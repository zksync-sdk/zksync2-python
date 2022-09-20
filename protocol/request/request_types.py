from dataclasses import dataclass
from typing import TypedDict, List, Optional
from eth_typing import HexStr
from web3 import Web3
from web3.types import AccessList
from protocol.core.types import PaymasterParams
from protocol.utility_contracts.contract_deployer import ContractDeployer
from protocol.utility_contracts.deploy_addresses import ZkSyncAddresses


@dataclass
class EIP712Meta(dict):
    ERGS_PER_PUB_DATA_DEFAULT = 160000

    ergs_per_pub_data: int = ERGS_PER_PUB_DATA_DEFAULT
    custom_signature: Optional[bytes] = None
    factory_deps: Optional[List[bytes]] = None
    paymaster_params: Optional[PaymasterParams] = None


Transaction = TypedDict(
    "Transaction",
    {
        "from": HexStr,
        "to": HexStr,
        "gas": int,
        "gasPrice": int,
        "value": int,
        "data": HexStr,
        "transactionType": int,
        "accessList": Optional[AccessList],
        "eip712Meta": EIP712Meta,
    }, total=False)


class TransactionType:
    EIP_712_TX_TYPE = 113


def create_function_call_transaction(from_: HexStr,
                                     to: HexStr,
                                     ergs_price: int,
                                     ergs_limit: int,
                                     data: HexStr,
                                     value: int = 0):
    eip712_meta_default = EIP712Meta()
    tx: Transaction = {
        "from": from_,
        "to": to,
        "gas": ergs_limit,
        "gasPrice": ergs_price,
        "value": value,
        "data": data,
        "transactionType": TransactionType.EIP_712_TX_TYPE,
        "eip712Meta": eip712_meta_default
    }
    return tx


def create2_contract_transaction(web3: Web3,
                                 from_: HexStr,
                                 ergs_price: int,
                                 ergs_limit: int,
                                 bytecode: bytes,
                                 deps: List[bytes] = None,
                                 call_data: Optional[bytes] = None,
                                 value: int = 0):
    contract_deployer = ContractDeployer(web3)
    call_data = contract_deployer.encode_create2(bytecode=bytecode,
                                                 call_data=call_data)
    factory_deps = []
    if deps is not None:
        for dep in deps:
            factory_deps.append(dep)
    factory_deps.append(bytecode)

    eip712_meta = EIP712Meta(ergs_per_pub_data=EIP712Meta.ERGS_PER_PUB_DATA_DEFAULT,
                             custom_signature=None,
                             factory_deps=factory_deps,
                             paymaster_params=None)
    tx: Transaction = {
        "from": from_,
        "to": Web3.toChecksumAddress(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
        "gas": ergs_limit,
        "gasPrice": ergs_price,
        "value": value,
        "data": HexStr(call_data),
        "transactionType": TransactionType.EIP_712_TX_TYPE,
        "eip712Meta": eip712_meta
    }
    return tx


def create_contract_transaction(web3: Web3,
                                from_: HexStr,
                                ergs_price: int,
                                ergs_limit: int,
                                bytecode: bytes,
                                deps: List[bytes] = None,
                                call_data: Optional[bytes] = None,
                                value: int = 0):
    contract_deployer = ContractDeployer(web3)
    call_data = contract_deployer.encode_create(bytecode=bytecode,
                                                call_data=call_data)
    factory_deps = []
    if deps is not None:
        for dep in deps:
            factory_deps.append(dep)
    factory_deps.append(bytecode)
    eip712_meta = EIP712Meta(ergs_per_pub_data=EIP712Meta.ERGS_PER_PUB_DATA_DEFAULT,
                             custom_signature=None,
                             factory_deps=factory_deps,
                             paymaster_params=None)

    tx: Transaction = {
        "from": from_,
        "to": Web3.toChecksumAddress(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
        "gas": ergs_limit,
        "gasPrice": ergs_price,
        "value": value,
        "data": HexStr(call_data),
        "transactionType": TransactionType.EIP_712_TX_TYPE,
        "eip712Meta": eip712_meta
    }
    return tx
