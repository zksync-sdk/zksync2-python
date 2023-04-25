import os
from unittest import TestCase

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

from test_config import LOCAL_ENV, EnvPrivateKey
from zksync2.core.utils import RecommendedGasLimit
from zksync2.manage_contracts.zksync_contract import ZkSyncContract
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner


def generate_random_salt() -> bytes:
    return os.urandom(32)


class ZkSyncWeb3Tests(TestCase):

    def setUp(self) -> None:
        env = LOCAL_ENV
        env_key = EnvPrivateKey("ZKSYNC_KEY1")
        self.zksync = ZkSyncBuilder.build(env.zksync_server)
        self.eth_web3 = Web3(Web3.HTTPProvider(env.eth_server))
        self.account: LocalAccount = Account.from_key(env_key.key)
        self.chain_id = self.zksync.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.zksync_contract = ZkSyncContract(self.zksync.zksync.zks_main_contract(),
                                              self.eth_web3,
                                              self.account)

    def test_facet_addresses_call(self):
        facets = self.zksync_contract.facets()
        for facet in facets:
            print(f"{facet}")

    def test_get_current_proposal_id(self):
        current_id = self.zksync_contract.get_current_proposal_id()
        print(f"ID: {current_id}")

    def test_get_first_unprocessed_priority_tx(self):
        tx = self.zksync_contract.get_first_unprocessed_priority_tx()
        print(f"{tx}")

    def test_get_governor(self):
        governor = self.zksync_contract.get_governor()
        print(f"Governor: {governor}")

    def test_get_l2_bootloader_bytecode_hash(self):
        bytecode_hash = self.zksync_contract.get_l2_bootloader_bytecode_hash()
        print(f"Hash: {bytecode_hash.hex()}")

    def test_get_l2_default_account_bytecode_hash(self):
        bytecode_hash = self.zksync_contract.get_l2_default_account_bytecode_hash()
        print(f"Hash: {bytecode_hash.hex()}")

    def test_get_proposed_upgrade_hash(self):
        upgrade_hash = self.zksync_contract.get_proposed_upgrade_hash()
        print(f"Hash: {upgrade_hash.hex()}")

    def test_get_proposed_upgrade_timestamp(self):
        upgrade_timestamp = self.zksync_contract.get_proposed_upgrade_timestamp()
        print(f"Time stamp : {upgrade_timestamp}")

    def test_get_total_blocks_committed(self):
        total = self.zksync_contract.get_total_blocks_committed()
        print(f"Total: {total}")

    def test_get_total_blocks_executed(self):
        total = self.zksync_contract.get_total_blocks_executed()
        print(f"Total: {total}")

    def test_get_total_blocks_verified(self):
        total = self.zksync_contract.get_total_blocks_verified()
        print(f"Total: {total}")

    def test_get_total_priority_txs(self):
        priority = self.zksync_contract.get_total_priority_txs()
        print(f"Priority: {priority}")

    def test_get_priority_tx_max_gas_limit(self):
        v = self.zksync_contract.get_priority_tx_max_gas_limit()
        print(f"max gas limit: {v}")

    def test_is_approved_by_security_council(self):
        v = self.zksync_contract.is_approved_by_security_council()
        print(f"Is approved: {v}")

    def test_is_diamond_storage_frozen(self):
        v = self.zksync_contract.is_diamond_storage_frozen()
        print(f"Is dimond: {v}")

    def test_get_verifier(self):
        verifier = self.zksync_contract.get_verifier()
        print(f"Verifier: {verifier}")

    def test_get_verifier_params(self):
        verifier_params = self.zksync_contract.get_verifier_params()
        print(f"Verifier params: {verifier_params}")

    def test_request_l2_transaction(self):
        RECOMMENDED_DEPOSIT_L2_GAS_LIMIT = 10000000
        DEPOSIT_GAS_PER_PUBDATA_LIMIT = 50000
        gas_price = self.eth_web3.eth.gas_price
        gas_limit = RecommendedGasLimit.EXECUTE.value
        l2_value = 0
        tx_receipt = self.zksync_contract.request_l2_transaction(self.zksync_contract.address,
                                                                 l2_value,
                                                                 b'',
                                                                 RECOMMENDED_DEPOSIT_L2_GAS_LIMIT,
                                                                 DEPOSIT_GAS_PER_PUBDATA_LIMIT,
                                                                 [],
                                                                 self.zksync_contract.address,
                                                                 gas_price,
                                                                 gas_limit,
                                                                 0)
        print(f"receipt: {tx_receipt}")
