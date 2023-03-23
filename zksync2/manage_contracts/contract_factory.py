import json
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Any
from eth_account.signers.base import BaseAccount
from eth_utils import remove_0x_prefix
from web3 import Web3
from web3.contract import Contract
from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.signer.eth_signer import EthSignerBase
from zksync2.transaction.transaction_builders import TxCreateContract, TxCreate2Contract


class DeploymentType(Enum):
    CREATE = auto()
    CREATE2 = auto()


class LegacyContractFactory:

    @classmethod
    def from_json(cls,
                  zksync: Web3,
                  compiled_contract: Path,
                  account: BaseAccount,
                  signer: EthSignerBase,
                  deployment_type: DeploymentType = DeploymentType.CREATE):
        with compiled_contract.open(mode='r') as json_f:
            data = json.load(json_f)
            bytecode = bytes.fromhex(remove_0x_prefix(data["bytecode"]))
            return cls(zksync=zksync,
                       abi=data["abi"],
                       bytecode=bytecode,
                       account=account,
                       signer=signer,
                       deployment_type=deployment_type)

    def __init__(self,
                 zksync: Web3,
                 abi,
                 bytecode,
                 account: BaseAccount,
                 signer: EthSignerBase,
                 deployment_type: DeploymentType = DeploymentType.CREATE):
        self.web3 = zksync
        self.abi = abi
        self.byte_code = bytecode
        self.account = account
        self.type = deployment_type
        self.signer = signer

    def _deploy_create(self,
                       salt: bytes = None,
                       args: Optional[Any] = None,
                       deps: List[bytes] = None) -> Contract:
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        call_data = None
        if args is not None:
            encoder = ContractEncoder(self.web3, abi=self.abi, bytecode=self.byte_code)
            call_data = encoder.encode_constructor(args)

        factory_deps = None
        if deps is not None:
            factory_deps = deps

        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.web3.zksync.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,
                                           gas_price=self.web3.zksync.gas_price,
                                           bytecode=self.byte_code,
                                           call_data=call_data,
                                           deps=factory_deps,
                                           salt=salt)

        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)

        tx_712 = create_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        if factory_deps is not None:
            contract_deployer = PrecomputeContractDeployer(self.web3)
            contract_address = contract_deployer.extract_contract_address(tx_receipt)
        else:
            contract_address = tx_receipt["contractAddress"]
        return self.web3.zksync.contract(address=contract_address,
                                         abi=self.abi)

    def _deploy_create2(self,
                        salt: bytes = None,
                        args: Optional[Any] = None,
                        deps: List[bytes] = None) -> Contract:

        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price
        call_data = None
        if args is not None:
            encoder = ContractEncoder(self.web3, abi=self.abi, bytecode=self.byte_code)
            call_data = encoder.encode_constructor(args)

        factory_deps = None
        if deps is not None:
            factory_deps = deps

        create2_contract = TxCreate2Contract(web3=self.web3,
                                             chain_id=self.web3.zksync.chain_id,
                                             nonce=nonce,
                                             from_=self.account.address,
                                             gas_limit=0,
                                             gas_price=gas_price,
                                             bytecode=self.byte_code,
                                             call_data=call_data,
                                             deps=factory_deps,
                                             salt=salt)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)
        tx_712 = create2_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)

        if factory_deps is not None:
            contract_deployer = PrecomputeContractDeployer(self.web3)
            contract_address = contract_deployer.extract_contract_address(tx_receipt)
        else:
            contract_address = tx_receipt["contractAddress"]
        return self.web3.zksync.contract(address=contract_address,
                                         abi=self.abi)

    def deploy(self,
               salt: bytes = None,
               args: Optional[Any] = None,
               deps: List[bytes] = None) -> Contract:
        if self.type == DeploymentType.CREATE2:
            return self._deploy_create2(salt, args, deps)
        return self._deploy_create(salt, args, deps)
