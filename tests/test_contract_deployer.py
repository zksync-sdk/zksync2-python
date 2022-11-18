from unittest import TestCase

from eth_typing import HexStr
from eth_utils import add_0x_prefix
from zksync2.core.utils import hash_byte_code
from tests.contracts.utils import get_hex_binary


class ContractDeployerTests(TestCase):

    def test_hash_byte_code(self):
        expected = "0x010000517112c421df08d7b49e4dc1312f4ee62268ee4f5683b11d9e2d33525a"
        counter_contract_bin = get_hex_binary("counter_contract.hex")
        hash_bytes = hash_byte_code(counter_contract_bin)
        result = add_0x_prefix(HexStr(hash_bytes.hex()))
        self.assertEqual(result, expected)
