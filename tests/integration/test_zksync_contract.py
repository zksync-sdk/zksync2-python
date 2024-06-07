import os
from unittest import TestCase

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

from tests.unit.test_config import LOCAL_ENV, EnvPrivateKey
from zksync2.core.utils import RecommendedGasLimit
from zksync2.manage_contracts.utils import get_zksync_hyperchain
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner


def generate_random_salt() -> bytes:
    return os.urandom(32)


class ZkSyncWeb3Tests(TestCase):
    def setUp(self) -> None:
        env = LOCAL_ENV
        env_key = "0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110"
        self.zksync = ZkSyncBuilder.build(env.zksync_server)
        self.eth_web3 = Web3(Web3.HTTPProvider(env.eth_server))
        self.account: LocalAccount = Account.from_key(env_key)
        self.chain_id = self.zksync.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.zksync_contract = self.eth_web3.eth.contract(
            Web3.to_checksum_address(self.zksync.zksync.zks_main_contract()),
            abi=get_zksync_hyperchain(),
        )

    def test_facet_addresses_call(self):
        facets = self.zksync_contract.functions.facets().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_get_first_unprocessed_priority_tx(self):
        tx = self.zksync_contract.functions.getFirstUnprocessedPriorityTx().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_get_l2_bootloader_bytecode_hash(self):
        bytecode_hash = (
            self.zksync_contract.functions.getL2BootloaderBytecodeHash().call(
                {
                    "chainId": self.eth_web3.eth.chain_id,
                    "from": self.account.address,
                    "nonce": self.eth_web3.eth.get_transaction_count(
                        self.account.address
                    ),
                }
            )
        )

    def test_get_l2_default_account_bytecode_hash(self):
        bytecode_hash = (
            self.zksync_contract.functions.getL2DefaultAccountBytecodeHash().call(
                {
                    "chainId": self.eth_web3.eth.chain_id,
                    "from": self.account.address,
                    "nonce": self.eth_web3.eth.get_transaction_count(
                        self.account.address
                    ),
                }
            )
        )

    def test_get_proposed_upgrade_timestamp(self):
        upgrade_timestamp = self.zksync_contract.functions.getPriorityQueueSize().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_get_total_blocks_committed(self):
        total = self.zksync_contract.functions.getProtocolVersion().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_get_total_blocks_executed(self):
        total = self.zksync_contract.functions.getTotalBatchesCommitted().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_get_total_blocks_verified(self):
        total = self.zksync_contract.functions.getTotalBatchesExecuted().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_get_total_priority_txs(self):
        priority = self.zksync_contract.functions.getTotalBatchesVerified().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_is_diamond_storage_frozen(self):
        v = self.zksync_contract.functions.isDiamondStorageFrozen().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_get_verifier(self):
        verifier = self.zksync_contract.functions.getVerifier().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_get_verifier_params(self):
        verifier_params = ret = self.zksync_contract.functions.getVerifierParams().call(
            {
                "chainId": self.eth_web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
            }
        )

    def test_request_l2_transaction(self):
        RECOMMENDED_DEPOSIT_L2_GAS_LIMIT = 10000000
        DEPOSIT_GAS_PER_PUBDATA_LIMIT = 50000
        gas_price = self.eth_web3.eth.gas_price
        gas_limit = RecommendedGasLimit.EXECUTE.value
        l2_value = 0
        contract = self.eth_web3.eth.contract(
            Web3.to_checksum_address(self.zksync.zksync.zks_main_contract()),
            abi=get_zksync_hyperchain(),
        )
        tx = contract.functions.requestL2Transaction(
            Web3.to_checksum_address(self.zksync.zksync.zks_main_contract()),
            l2_value,
            b"",
            RECOMMENDED_DEPOSIT_L2_GAS_LIMIT,
            DEPOSIT_GAS_PER_PUBDATA_LIMIT,
            [],
            Web3.to_checksum_address(self.zksync.zksync.zks_main_contract()),
        ).build_transaction(
            {
                "nonce": self.eth_web3.eth.get_transaction_count(self.account.address),
                "from": self.account.address,
                "gasPrice": gas_price,
                "gas": gas_limit,
                "value": 0,
            }
        )
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.eth_web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.eth_web3.eth.wait_for_transaction_receipt(tx_hash)
