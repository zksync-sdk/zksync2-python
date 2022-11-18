from unittest import TestCase

from eth_typing import HexStr
from eth_utils import add_0x_prefix
from web3 import Web3
from web3.types import Nonce

from zksync2.core.utils import hash_byte_code
from tests.contracts.utils import get_hex_binary
from zksync2.manage_contracts.contract_deployer import ContractDeployer
from zksync2.module.module_builder import ZkSyncBuilder


class ContractDeployerTests(TestCase):
    ZKSYNC_TEST_URL = "https://zksync2-testnet.zksync.dev"

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.ZKSYNC_TEST_URL)
        self.contract_deployer = ContractDeployer(self.web3)
        self.counter_contract_bin = get_hex_binary("counter_contract.hex")

    def test_compute_l2_create2(self):
        expected = Web3.toChecksumAddress("0x0790aff699b38f40929840469a72fb40e9763716")
        sender = HexStr("0xa909312acfc0ed4370b8bd20dfe41c8ff6595194")
        salt = b'\0' * 32
        counter_contract_bin = get_hex_binary("counter_contract.hex")
        addr = self.contract_deployer.compute_l2_create2_address(sender, counter_contract_bin, b'', salt)
        self.assertEqual(expected, addr)

    def test_compute_l2_create(self):
        expected = Web3.toChecksumAddress("0x5107b7154dfc1d3b7f1c4e19b5087e1d3393bcf4")
        sender = HexStr("0x7e5f4552091a69125d5dfcb7b8c2659029395bdf")
        addr = self.contract_deployer.compute_l2_create_address(sender, Nonce(3))
        self.assertEqual(expected, addr)

    def test_hash_byte_code(self):
        expected = "0x010000517112c421df08d7b49e4dc1312f4ee62268ee4f5683b11d9e2d33525a"
        hash_bytes = hash_byte_code(self.counter_contract_bin)
        result = add_0x_prefix(HexStr(hash_bytes.hex()))
        self.assertEqual(result, expected)
