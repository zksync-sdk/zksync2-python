# from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from web3._utils.compat import (
    TypedDict,
)

from eth_typing import HexStr
from web3.types import AccessList
from zksync2.core.types import PaymasterParams


@dataclass
class EIP712Meta:
    ERGS_PER_PUB_DATA_DEFAULT = 16 * 10000

    ergs_per_pub_data: int = ERGS_PER_PUB_DATA_DEFAULT
    custom_signature: Optional[bytes] = None
    factory_deps: Optional[List[bytes]] = None
    paymaster_params: Optional[PaymasterParams] = None


Transaction = TypedDict("Transaction", {
        "chain_id": int,  # NEW
        "nonce": int,  # NEW
        "from": HexStr,
        "to": HexStr,
        "gas": int,
        "gasPrice": int,
        "maxPriorityFeePerGas": int,  # NEW
        "value": int,
        "data": HexStr,
        "transactionType": int,
        "accessList": Optional[AccessList],
        "eip712Meta": EIP712Meta,
}, total=False)


class TransactionType(Enum):
    EIP_712_TX_TYPE = 113

#
# def create2_contract_transaction(web3: Web3,
#                                  from_: HexStr,
#                                  ergs_price: int,
#                                  ergs_limit: int,
#                                  bytecode: bytes,
#                                  deps: List[bytes] = None,
#                                  call_data: Optional[bytes] = None,
#                                  value: int = 0,
#                                  salt: Optional[bytes] = None):
#     contract_deployer = ContractDeployer(web3)
#     call_data = contract_deployer.encode_create2(bytecode=bytecode,
#                                                  call_data=call_data,
#                                                  salt=salt)
#     factory_deps = []
#     if deps is not None:
#         for dep in deps:
#             factory_deps.append(dep)
#     factory_deps.append(bytecode)
#
#     eip712_meta = EIP712Meta(ergs_per_pub_data=EIP712Meta.ERGS_PER_PUB_DATA_DEFAULT,
#                              custom_signature=None,
#                              factory_deps=factory_deps,
#                              paymaster_params=None)
#     tx: Transaction = {
#         "from": from_,
#         "to": Web3.toChecksumAddress(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
#         "gas": ergs_limit,
#         "gasPrice": ergs_price,
#         "value": value,
#         "data": HexStr(call_data),
#         "transactionType": TransactionType.EIP_712_TX_TYPE.value,
#         "eip712Meta": eip712_meta
#     }
#     return tx

#
# def create_contract_transaction(web3: Web3,
#                                 from_: HexStr,
#                                 ergs_price: int,
#                                 ergs_limit: int,
#                                 bytecode: bytes,
#                                 deps: List[bytes] = None,
#                                 call_data: Optional[bytes] = None,
#                                 value: int = 0,
#                                 salt: Optional[bytes] = None):
#     contract_deployer = ContractDeployer(web3)
#     call_data = contract_deployer.encode_create(bytecode=bytecode,
#                                                 call_data=call_data,
#                                                 salt_data=salt)
#     factory_deps = []
#     if deps is not None:
#         for dep in deps:
#             factory_deps.append(dep)
#     factory_deps.append(bytecode)
#     eip712_meta = EIP712Meta(ergs_per_pub_data=EIP712Meta.ERGS_PER_PUB_DATA_DEFAULT,
#                              custom_signature=None,
#                              factory_deps=factory_deps,
#                              paymaster_params=None)
#     tx: Transaction = {
#         "from": from_,
#         "to": Web3.toChecksumAddress(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
#         "gas": ergs_limit,
#         "gasPrice": ergs_price,
#         "value": value,
#         "data": HexStr(call_data),
#         "transactionType": TransactionType.EIP_712_TX_TYPE.value,
#         "eip712Meta": eip712_meta
#     }
#     return tx
