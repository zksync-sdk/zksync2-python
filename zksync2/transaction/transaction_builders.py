from abc import ABC
from typing import Optional, List

from eth_account.signers.base import BaseAccount
from eth_typing import HexStr
from web3 import Web3
from web3.types import Nonce

from zksync2.core.types import Token, BridgeAddresses, L2_ETH_TOKEN_ADDRESS
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.eth_token import EthToken
from zksync2.manage_contracts.l2_bridge import L2Bridge
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.module.request_types import EIP712Meta, TransactionType, Transaction as ZkTx
from zksync2.transaction.transaction712 import Transaction712


class TxBase(ABC):

    def __init__(self, trans: ZkTx):
        self.tx_: ZkTx = trans

    @property
    def tx(self) -> ZkTx:
        return self.tx_

    def tx712(self, estimated_gas: int) -> Transaction712:
        return Transaction712(chain_id=self.tx["chain_id"],
                              nonce=Nonce(self.tx["nonce"]),
                              gas_limit=estimated_gas,
                              to=self.tx["to"],
                              value=self.tx["value"],
                              data=self.tx["data"],
                              maxPriorityFeePerGas=self.tx["maxPriorityFeePerGas"],
                              maxFeePerGas=self.tx["gasPrice"],
                              from_=self.tx["from"],
                              meta=self.tx["eip712Meta"])


class TxFunctionCall(TxBase, ABC):

    def __init__(self,
                 chain_id: int,
                 nonce: int,
                 from_: HexStr,
                 to: HexStr,
                 value: int = 0,
                 data: HexStr = HexStr("0x"),
                 gas_limit: int = 0,
                 gas_price: int = 0,
                 max_priority_fee_per_gas=100_000_000,
                 paymaster_params=None,
                 custom_signature=None):
        eip712_meta = EIP712Meta(gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
                                 custom_signature=custom_signature,
                                 factory_deps=None,
                                 paymaster_params=paymaster_params)

        super(TxFunctionCall, self).__init__(
            trans={
                "chain_id": chain_id,
                "nonce": nonce,
                "from": from_,
                "to": to,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "value": value,
                "data": data,
                "transactionType": TransactionType.EIP_712_TX_TYPE.value,
                "eip712Meta": eip712_meta
            })


class TxCreateContract(TxBase, ABC):

    def __init__(self,
                 web3: Web3,
                 chain_id: int,
                 nonce: int,
                 from_: HexStr,
                 bytecode: bytes,
                 gas_price: int,
                 gas_limit: int = 0,
                 deps: List[bytes] = None,
                 call_data: Optional[bytes] = None,
                 value: int = 0,
                 max_priority_fee_per_gas=100_000_000
                 ):
        contract_deployer = PrecomputeContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create(bytecode=bytecode, call_data=call_data)
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)
        eip712_meta = EIP712Meta(gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
                                 custom_signature=None,
                                 factory_deps=factory_deps,
                                 paymaster_params=None)

        super(TxCreateContract, self).__init__(trans={
            "chain_id": chain_id,
            "nonce": nonce,
            "from": from_,
            "to": Web3.to_checksum_address(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
            "gas": gas_limit,
            "gasPrice": gas_price,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "value": value,
            "data": HexStr(generated_call_data),
            "transactionType": TransactionType.EIP_712_TX_TYPE.value,
            "eip712Meta": eip712_meta
        })


class TxCreate2Contract(TxBase, ABC):

    def __init__(self,
                 web3: Web3,
                 chain_id: int,
                 nonce: int,
                 from_: HexStr,
                 gas_limit: int,
                 gas_price: int,
                 bytecode: bytes,
                 deps: List[bytes] = None,
                 call_data: Optional[bytes] = None,
                 value: int = 0,
                 max_priority_fee_per_gas=100_000_000,
                 salt: Optional[bytes] = None
                 ):
        contract_deployer = PrecomputeContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create2(bytecode=bytecode,
                                                               call_data=call_data,
                                                               salt=salt)
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)

        eip712_meta = EIP712Meta(gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
                                 custom_signature=None,
                                 factory_deps=factory_deps,
                                 paymaster_params=None)
        super(TxCreate2Contract, self).__init__(trans={
            "chain_id": chain_id,
            "nonce": nonce,
            "from": from_,
            "to": Web3.to_checksum_address(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
            "gas": gas_limit,
            "gasPrice": gas_price,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "value": value,
            "data": HexStr(generated_call_data),
            "transactionType": TransactionType.EIP_712_TX_TYPE.value,
            "eip712Meta": eip712_meta
        })


class TxCreateAccount(TxBase, ABC):

    def __init__(self,
                 web3: Web3,
                 chain_id: int,
                 nonce: int,
                 from_: HexStr,
                 bytecode: bytes,
                 gas_price: int,
                 gas_limit: int = 0,
                 deps: List[bytes] = None,
                 call_data: Optional[bytes] = None,
                 value: int = 0,
                 max_priority_fee_per_gas=100_000_000
                 ):
        contract_deployer = PrecomputeContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create_account(bytecode=bytecode, call_data=call_data)
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)
        eip712_meta = EIP712Meta(gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
                                 custom_signature=None,
                                 factory_deps=factory_deps,
                                 paymaster_params=None)

        super(TxCreateAccount, self).__init__(trans={
            "chain_id": chain_id,
            "nonce": nonce,
            "from": from_,
            "to": Web3.to_checksum_address(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
            "gas": gas_limit,
            "gasPrice": gas_price,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "value": value,
            "data": HexStr(generated_call_data),
            "transactionType": TransactionType.EIP_712_TX_TYPE.value,
            "eip712Meta": eip712_meta
        })


class TxCreate2Account(TxBase, ABC):

    def __init__(self,
                 web3: Web3,
                 chain_id: int,
                 nonce: int,
                 from_: HexStr,
                 gas_limit: int,
                 gas_price: int,
                 bytecode: bytes,
                 deps: List[bytes] = None,
                 call_data: Optional[bytes] = None,
                 value: int = 0,
                 max_priority_fee_per_gas=100_000_000,
                 salt: Optional[bytes] = None
                 ):
        contract_deployer = PrecomputeContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create2_account(bytecode=bytecode,
                                                                       call_data=call_data,
                                                                       salt=salt)
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)

        eip712_meta = EIP712Meta(gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
                                 custom_signature=None,
                                 factory_deps=factory_deps,
                                 paymaster_params=None)
        super(TxCreate2Account, self).__init__(trans={
            "chain_id": chain_id,
            "nonce": nonce,
            "from": from_,
            "to": Web3.to_checksum_address(ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value),
            "gas": gas_limit,
            "gasPrice": gas_price,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "value": value,
            "data": HexStr(generated_call_data),
            "transactionType": TransactionType.EIP_712_TX_TYPE.value,
            "eip712Meta": eip712_meta
        })


class TxWithdraw(TxBase, ABC):

    def __init__(self,
                 web3: Web3,
                 token: Token,
                 amount: int,
                 gas_limit: int,
                 account: BaseAccount,
                 gas_price: int = None,
                 to: HexStr = None,
                 bridge_address: HexStr = None):

        # INFO: send to self
        if to is None:
            to = account.address

        if token.is_eth():
            eth_l2_token = EthToken(web3=web3.zksync,
                                    contract_address=L2_ETH_TOKEN_ADDRESS,
                                    account=account)

            tx = eth_l2_token.withdraw_tx(to=to,
                                          amount=amount,
                                          gas=gas_limit,
                                          gas_price=gas_price)
        else:
            if bridge_address is None:
                bridge_addresses: BridgeAddresses = web3.zksync.zks_get_bridge_contracts()
                bridge_address = bridge_addresses.erc20_l2_default_bridge
            l2_bridge = L2Bridge(contract_address=bridge_address,
                                 web3_zks=web3,
                                 zksync_account=account)
            tx = l2_bridge.withdraw_tx(l1_receiver=to,
                                       l2_token=token.l2_address,
                                       amount=amount,
                                       gas=gas_limit,
                                       gas_price=gas_price)
        super(TxWithdraw, self).__init__(trans=tx)

    @property
    def tx(self) -> ZkTx:
        return self.tx_

    def estimated_gas(self, estimated_gas: int) -> ZkTx:
        self.tx_['gas'] = estimated_gas
        return self.tx_
