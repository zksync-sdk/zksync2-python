from unittest import TestCase

from eth_typing import HexStr
from web3 import Web3

from tests.integration.test_config import LOCAL_ENV, EnvPrivateKey
from zksync2.core.types import BridgeAddresses
from zksync2.core.utils import apply_l1_to_l2_alias, undo_l1_to_l2_alias
from zksync2.module.module_builder import ZkSyncBuilder


class UtilsTest(TestCase):
    def setUp(self) -> None:
        self.env = LOCAL_ENV
        env_key = EnvPrivateKey("ZKSYNC_KEY1")
        self.zksync = ZkSyncBuilder.build(self.env.zksync_server)

    def test_apply_l1_to_l2_alias(self):
        l1_contract_address = HexStr("0x702942B8205E5dEdCD3374E5f4419843adA76Eeb")
        l2_contract_address = apply_l1_to_l2_alias(l1_contract_address)
        self.assertEqual(
            l2_contract_address.lower(),
            "0x813A42B8205E5DedCd3374e5f4419843ADa77FFC".lower(),
        )

    def test_undo_l1_to_l2_alias(self):
        l2_contract_address = HexStr("0x813A42B8205E5DedCd3374e5f4419843ADa77FFC")
        l1_contract_address = undo_l1_to_l2_alias(l2_contract_address)
        self.assertEqual(
            l1_contract_address.lower(),
            "0x702942B8205E5dEdCD3374E5f4419843adA76Eeb".lower(),
        )
