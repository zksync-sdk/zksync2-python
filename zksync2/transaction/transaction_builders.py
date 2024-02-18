from abc import ABC
from typing import Optional, List

from eth_account.signers.base import BaseAccount
from eth_typing import HexStr
from web3 import Web3
from web3.types import Nonce

from zksync2.core.types import Token, BridgeAddresses, TransactionOptions
from zksync2.core.utils import is_eth, MAX_PRIORITY_FEE_PER_GAS
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.precompute_contract_deployer import (
    PrecomputeContractDeployer,
)
from zksync2.manage_contracts.utils import (
    l2_bridge_abi_default,
    eth_token_abi_default,
    get_erc20_abi,
)
from zksync2.module.request_types import (
    EIP712Meta,
    TransactionType,
    Transaction as ZkTx,
)
from zksync2.transaction.transaction712 import Transaction712

L2_ETH_TOKEN_ADDRESS = HexStr("0x000000000000000000000000000000000000800a")


class TxBase(ABC):
    def __init__(self, trans: ZkTx):
        self.tx_: ZkTx = trans

    @property
    def tx(self) -> ZkTx:
        return self.tx_

    def tx712(self, estimated_gas: int) -> Transaction712:
        return Transaction712(
            chain_id=self.tx["chain_id"],
            nonce=Nonce(self.tx["nonce"]),
            gas_limit=estimated_gas,
            to=self.tx["to"],
            value=self.tx["value"],
            data=self.tx["data"],
            maxPriorityFeePerGas=self.tx["maxPriorityFeePerGas"],
            maxFeePerGas=self.tx["gasPrice"],
            from_=self.tx["from"],
            meta=self.tx["eip712Meta"],
        )


class TxFunctionCall(TxBase, ABC):
    def __init__(
        self,
        from_: HexStr,
        to: HexStr,
        value: int = 0,
        chain_id: int = None,
        nonce: int = None,
        data: HexStr = HexStr("0x"),
        gas_limit: int = 0,
        gas_price: int = 0,
        max_priority_fee_per_gas: int = MAX_PRIORITY_FEE_PER_GAS,
        paymaster_params=None,
        custom_signature=None,
        gas_per_pub_data: int = EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
    ):
        eip712_meta = EIP712Meta(
            gas_per_pub_data=gas_per_pub_data,
            custom_signature=custom_signature,
            factory_deps=None,
            paymaster_params=paymaster_params,
        )

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
                "eip712Meta": eip712_meta,
            }
        )


class TxCreateContract(TxBase, ABC):
    def __init__(
        self,
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
        max_priority_fee_per_gas=100_000_000,
    ):
        contract_deployer = PrecomputeContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create(
            bytecode=bytecode, call_data=call_data
        )
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)
        eip712_meta = EIP712Meta(
            gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
            custom_signature=None,
            factory_deps=factory_deps,
            paymaster_params=None,
        )

        super(TxCreateContract, self).__init__(
            trans={
                "chain_id": chain_id,
                "nonce": nonce,
                "from": from_,
                "to": Web3.to_checksum_address(
                    ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value
                ),
                "gas": gas_limit,
                "gasPrice": gas_price,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "value": value,
                "data": HexStr(generated_call_data),
                "transactionType": TransactionType.EIP_712_TX_TYPE.value,
                "eip712Meta": eip712_meta,
            }
        )


class TxCreate2Contract(TxBase, ABC):
    def __init__(
        self,
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
        salt: Optional[bytes] = None,
    ):
        contract_deployer = PrecomputeContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create2(
            bytecode=bytecode, call_data=call_data, salt=salt
        )
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)

        eip712_meta = EIP712Meta(
            gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
            custom_signature=None,
            factory_deps=factory_deps,
            paymaster_params=None,
        )
        super(TxCreate2Contract, self).__init__(
            trans={
                "chain_id": chain_id,
                "nonce": nonce,
                "from": from_,
                "to": Web3.to_checksum_address(
                    ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value
                ),
                "gas": gas_limit,
                "gasPrice": gas_price,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "value": value,
                "data": HexStr(generated_call_data),
                "transactionType": TransactionType.EIP_712_TX_TYPE.value,
                "eip712Meta": eip712_meta,
            }
        )


class TxCreateAccount(TxBase, ABC):
    def __init__(
        self,
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
        max_priority_fee_per_gas=100_000_000,
    ):
        contract_deployer = PrecomputeContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create_account(
            bytecode=bytecode, call_data=call_data
        )
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)
        eip712_meta = EIP712Meta(
            gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
            custom_signature=None,
            factory_deps=factory_deps,
            paymaster_params=None,
        )

        super(TxCreateAccount, self).__init__(
            trans={
                "chain_id": chain_id,
                "nonce": nonce,
                "from": from_,
                "to": Web3.to_checksum_address(
                    ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value
                ),
                "gas": gas_limit,
                "gasPrice": gas_price,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "value": value,
                "data": HexStr(generated_call_data),
                "transactionType": TransactionType.EIP_712_TX_TYPE.value,
                "eip712Meta": eip712_meta,
            }
        )


class TxCreate2Account(TxBase, ABC):
    def __init__(
        self,
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
        salt: Optional[bytes] = None,
    ):
        contract_deployer = PrecomputeContractDeployer(web3)
        generated_call_data = contract_deployer.encode_create2_account(
            bytecode=bytecode, call_data=call_data, salt=salt
        )
        factory_deps = []
        if deps is not None:
            for dep in deps:
                factory_deps.append(dep)
        factory_deps.append(bytecode)

        eip712_meta = EIP712Meta(
            gas_per_pub_data=EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
            custom_signature=None,
            factory_deps=factory_deps,
            paymaster_params=None,
        )
        super(TxCreate2Account, self).__init__(
            trans={
                "chain_id": chain_id,
                "nonce": nonce,
                "from": from_,
                "to": Web3.to_checksum_address(
                    ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value
                ),
                "gas": gas_limit,
                "gasPrice": gas_price,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "value": value,
                "data": HexStr(generated_call_data),
                "transactionType": TransactionType.EIP_712_TX_TYPE.value,
                "eip712Meta": eip712_meta,
            }
        )


class TxWithdraw(TxBase, ABC):
    def __init__(
        self,
        web3: Web3,
        token: HexStr,
        amount: int,
        gas_limit: int,
        account: BaseAccount,
        gas_price: int = None,
        to: HexStr = None,
        bridge_address: HexStr = None,
        chain_id: int = None,
        nonce: int = None,
        paymaster_params=None,
    ):
        # INFO: send to self
        if to is None:
            to = account.address
        if gas_price is None:
            gas_price = web3.zksync.gas_price
        if nonce is None:
            web3.zksync.get_transaction_count(account.address)

        eip712_meta = EIP712Meta(
            gas_per_pub_data=50000,
            custom_signature=None,
            factory_deps=None,
            paymaster_params=paymaster_params,
        )

        if is_eth(token):
            if chain_id is None:
                chain_id = web3.zksync.chain_id
            contract = web3.zksync.contract(
                Web3.to_checksum_address(L2_ETH_TOKEN_ADDRESS),
                abi=eth_token_abi_default(),
            )
            tx = contract.functions.withdraw(to).build_transaction(
                {
                    "nonce": nonce,
                    "chainId": chain_id,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                    "value": amount,
                    "from": account.address,
                }
            )
        else:
            l2_bridge = web3.eth.contract(
                address=Web3.to_checksum_address(bridge_address),
                abi=l2_bridge_abi_default(),
            )
            tx = l2_bridge.functions.withdraw(to, token, amount).build_transaction(
                {
                    "nonce": nonce,
                    "chainId": chain_id,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                    "value": 0,
                    "from": account.address,
                }
            )
        tx["eip712Meta"] = eip712_meta
        super(TxWithdraw, self).__init__(trans=tx)

    def tx712(self, estimated_gas: int) -> Transaction712:
        return Transaction712(
            chain_id=self.tx["chainId"],
            nonce=Nonce(self.tx["nonce"]),
            gas_limit=estimated_gas,
            to=self.tx["to"],
            value=self.tx["value"],
            data=self.tx["data"],
            maxPriorityFeePerGas=0,
            maxFeePerGas=self.tx["gasPrice"],
            from_=self.tx["from"],
            meta=self.tx["eip712Meta"],
        )

    @property
    def tx(self) -> ZkTx:
        return self.tx_

    def estimated_gas(self, estimated_gas: int) -> ZkTx:
        self.tx_["gas"] = estimated_gas
        return self.tx_


class TxTransfer(TxBase, ABC):
    def __init__(
        self,
        from_: HexStr,
        to: HexStr,
        web3=None,
        token: HexStr = None,
        value: int = 0,
        chain_id: int = None,
        nonce: int = None,
        data: HexStr = HexStr("0x"),
        gas_limit: int = 0,
        gas_price: int = 0,
        max_priority_fee_per_gas: int = MAX_PRIORITY_FEE_PER_GAS,
        paymaster_params=None,
        custom_signature=None,
        gas_per_pub_data: int = EIP712Meta.GAS_PER_PUB_DATA_DEFAULT,
    ):
        eip712_meta = EIP712Meta(
            gas_per_pub_data=gas_per_pub_data,
            custom_signature=custom_signature,
            factory_deps=None,
            paymaster_params=paymaster_params,
        )
        if is_eth(token):
            super(TxTransfer, self).__init__(
                trans={
                    "chainId": chain_id,
                    "nonce": nonce,
                    "from": from_,
                    "to": to,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                    "maxPriorityFeePerGas": max_priority_fee_per_gas,
                    "value": value,
                    "data": data,
                    "transactionType": TransactionType.EIP_712_TX_TYPE.value,
                    "eip712Meta": eip712_meta,
                }
            )
        else:
            token_contract = web3.contract(
                address=Web3.to_checksum_address(token),
                abi=get_erc20_abi(),
            )
            tx = token_contract.functions.transfer(to, value).build_transaction(
                {
                    "nonce": nonce,
                    "chainId": chain_id,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                    "from": from_,
                }
            )
            tx["eip712Meta"] = eip712_meta
            super(TxTransfer, self).__init__(trans=tx)

    def tx712(self, estimated_gas: int) -> Transaction712:
        return Transaction712(
            chain_id=self.tx["chainId"],
            nonce=Nonce(self.tx["nonce"]),
            gas_limit=estimated_gas,
            to=self.tx["to"],
            value=self.tx["value"],
            data=self.tx["data"],
            maxPriorityFeePerGas=0,
            maxFeePerGas=self.tx["gasPrice"],
            from_=self.tx["from"],
            meta=self.tx["eip712Meta"],
        )
