import os
from pathlib import Path
from unittest import TestCase

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr

from tests.integration.test_config import EnvURL, private_key_1
from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.contract_factory import (
    LegacyContractFactory,
    DeploymentType,
)
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner


def generate_random_salt() -> bytes:
    return os.urandom(32)


class ContractFactoryTest(TestCase):

    def setUp(self) -> None:
        self.env = EnvURL()
        self.provider = ZkSyncBuilder.build(self.env.env.zksync_server)
        self.account: LocalAccount = Account.from_key(private_key_1)
        self.chain_id = self.provider.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.counter_address = None
        self.test_tx_hash = None
        self.some_erc20_address = None

    def test_contract_factory_create(self):
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Counter.json")
        deployer = LegacyContractFactory.from_json(
            zksync=self.provider,
            compiled_contract=path.resolve(),
            account=self.account,
            signer=self.signer,
        )
        contract = deployer.deploy()
        self.assertIsNotNone(self.provider.zksync.get_code(contract.address))

    def test_contract_factory_crete2(self):
        salt = generate_random_salt()
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Counter.json")
        deployer = LegacyContractFactory.from_json(
            zksync=self.provider,
            compiled_contract=path.resolve(),
            account=self.account,
            signer=self.signer,
            deployment_type=DeploymentType.CREATE2,
        )
        contract = deployer.deploy(salt=salt)
        self.assertIsNotNone(self.provider.zksync.get_code(contract.address))

    def test_contract_factory_crete2_with_args(self):
        salt = generate_random_salt()
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Token.json")

        constructor_arguments = {"name_": "Ducat", "symbol_": "Ducat", "decimals_": 18}
        deployer = LegacyContractFactory.from_json(
            zksync=self.provider,
            compiled_contract=path.resolve(),
            account=self.account,
            signer=self.signer,
            deployment_type=DeploymentType.CREATE2,
        )
        contract = deployer.deploy(salt=salt, **constructor_arguments)
        self.assertIsNotNone(self.provider.zksync.get_code(contract.address))

    def test_deploy_paymaster(self):
        salt = generate_random_salt()
        directory = Path(__file__).parent
        path = directory / "../contracts/Paymaster.json"
        token_address = self.provider.to_checksum_address(
            "0x0183Fe07a98bc036d6eb23C3943d823bcD66a90F"
        )
        constructor_arguments = {"_erc20": token_address}

        deployer = LegacyContractFactory.from_json(
            zksync=self.provider,
            compiled_contract=path.resolve(),
            account=self.account,
            signer=self.signer,
            deployment_type=DeploymentType.CREATE2_ACCOUNT,
        )
        contract = deployer.deploy(salt=salt, **constructor_arguments)
        self.assertIsNotNone(self.provider.zksync.get_code(contract.address))
