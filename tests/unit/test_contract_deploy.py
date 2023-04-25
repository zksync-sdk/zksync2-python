from unittest import TestCase
from eth_typing import HexStr
from eth_utils import add_0x_prefix
from web3 import Web3
from web3.types import Nonce
from test_config import LOCAL_ENV
from zksync2.core.utils import hash_byte_code
from tests.contracts.utils import contract_path
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.module.module_builder import ZkSyncBuilder


class ContractDeployerTests(TestCase):

    def setUp(self) -> None:
        env = LOCAL_ENV
        self.web3 = ZkSyncBuilder.build(env.zksync_server)
        self.contract_deployer = PrecomputeContractDeployer(self.web3)
        counter_contract = ContractEncoder.from_json(self.web3, contract_path("Counter.json"))
        self.counter_contract_bin = counter_contract.bytecode

    def test_compute_l2_create2(self):
        expected = Web3.to_checksum_address("0xf7671F9178dF17CF2F94a51d5a97bF54f6dff25a")
        sender = HexStr("0xa909312acfc0ed4370b8bd20dfe41c8ff6595194")
        salt = b'\0' * 32
        addr = self.contract_deployer.compute_l2_create2_address(sender, self.counter_contract_bin, b'', salt)
        self.assertEqual(expected, addr)

    def test_compute_l2_create(self):
        expected = Web3.to_checksum_address("0x5107b7154dfc1d3b7f1c4e19b5087e1d3393bcf4")
        sender = HexStr("0x7e5f4552091a69125d5dfcb7b8c2659029395bdf")
        addr = self.contract_deployer.compute_l2_create_address(sender, Nonce(3))
        self.assertEqual(expected, addr)

    def test_hash_byte_code(self):
        expected = "0x0100003fcee62dec356138ff4ab621cb9ed313c17e98a4ec349b3e8e1642d588"
        hash_bytes = hash_byte_code(self.counter_contract_bin)
        result = add_0x_prefix(HexStr(hash_bytes.hex()))
        self.assertEqual(result, expected)
