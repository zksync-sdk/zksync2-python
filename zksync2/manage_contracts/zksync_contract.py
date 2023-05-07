import json
import importlib.resources as pkg_resources
from dataclasses import dataclass
from typing import List
from web3.contract.contract import ContractFunction
from web3.types import TxReceipt
from zksync2.manage_contracts import contract_abi
from eth_typing import HexStr
from eth_utils import remove_0x_prefix
from web3 import Web3
from eth_account.signers.base import BaseAccount

zksync_abi_cache = None


def _zksync_abi_default():
    global zksync_abi_cache

    if zksync_abi_cache is None:
        with pkg_resources.path(contract_abi, "IZkSync.json") as p:
            with p.open(mode='r') as json_file:
                data = json.load(json_file)
                zksync_abi_cache = data['abi']
    return zksync_abi_cache


@dataclass
class StoredBlockInfo:
    blockNumber: int
    blockHash: bytes
    indexRepeatedStorageChanges: int
    numberOfLayer1Txs: int
    priorityOperationsHash: bytes
    l2LogsTreeRoot: bytes
    timestamp: int
    commitment: bytes


@dataclass
class CommitBlockInfo:
    blockNumber: int
    timestamp: int
    indexRepeatedStorageChanges: int
    numberOfLayer1Txs: int
    l2LogsTreeRoot: bytes
    priorityOperationsHash: bytes
    initialStorageChanges: bytes
    repeatedStorageChanges: bytes
    l2Logs: bytes
    l2ArbitraryLengthMessages: List[bytes]
    factoryDeps: List[bytes]


@dataclass
class FacetCut:
    facet: HexStr
    action: int
    isFreezable: bool
    selectors: bytes


@dataclass
class DiamondCutData:
    facetCuts: List[FacetCut]
    initAddress: HexStr
    initCalldata: bytes


@dataclass
class Facet:
    addr: HexStr
    selectors: List[bytes]


@dataclass
class VerifierParams:
    recursionNodeLevelVkHash: bytes
    recursionLeafLevelVkHash: bytes
    recursionCircuitsSetVksHash: bytes


class ZkSyncContract:

    def __init__(self,
                 zksync_main_contract: HexStr,
                 eth: Web3,
                 account: BaseAccount):
        check_sum_address = Web3.to_checksum_address(zksync_main_contract)
        self.contract_address = check_sum_address
        self.web3 = eth
        self.contract = self.web3.eth.contract(self.contract_address, abi=_zksync_abi_default())
        self.account = account
        self.chain_id = self.web3.eth.chain_id

    @property
    def address(self):
        return self.contract_address

    def _nonce(self):
        return self.web3.eth.get_transaction_count(self.account.address)

    def _method_(self, method_name: str) -> ContractFunction:
        return getattr(self.contract.functions, method_name)

    def accept_governor(self):
        return self._method_("acceptGovernor")().call()

    def cancel_upgrade_proposal(self, proposed_upgrade_hash: HexStr):
        upgrade_hash = bytes.fromhex(remove_0x_prefix(proposed_upgrade_hash))
        self._method_("cancelUpgradeProposal")(upgrade_hash).call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def commit_blocks(self,
                      last_committed_block_data: StoredBlockInfo,
                      new_blocks_data: List[CommitBlockInfo]):
        raise NotImplementedError

    def execute_blocks(self,
                       _blocks_data: List[StoredBlockInfo]):
        raise NotImplementedError

    def execute_upgrade(self,
                        diamond_cut: DiamondCutData,
                        salt: bytes):
        raise NotImplementedError

    def facet_address(self, selector: bytes) -> HexStr:
        """
        INFO: might be int to be converted to bytes, because original type is bytes4
        """
        return self._method_("facetAddress")(selector).call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def facet_addresses(self) -> List[HexStr]:
        return self._method_("facetAddresses")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            }
        )

    def facet_function_selectors(self, facet: HexStr) -> List[bytes]:
        return self._method_("facetFunctionSelectors")(facet).call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            }
        )

    def facets(self) -> List[Facet]:
        facets = self._method_("facets")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            }
        )
        result = list()
        for facet in facets:
            result.append(Facet(facet[0], facet[1]))
        return result

    def finalize_eth_withdrawal(self,
                                l2_block_number: int,
                                l2_message_index: int,
                                l2_tx_number_in_block: int,
                                message: bytes,
                                merkle_proof: List[bytes]
                                ):
        tx = self._method_("finalizeEthWithdrawal")(l2_block_number,
                                                    l2_message_index,
                                                    l2_tx_number_in_block,
                                                    message,
                                                    merkle_proof).build_transaction(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def freeze_diamond(self):
        self._method_("freezeDiamond")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_current_proposal_id(self) -> int:
        return self._method_("getCurrentProposalId")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_first_unprocessed_priority_tx(self):
        return self._method_("getFirstUnprocessedPriorityTx")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_governor(self) -> HexStr:
        return self._method_("getGovernor")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_l2_bootloader_bytecode_hash(self) -> bytes:
        return self._method_("getL2BootloaderBytecodeHash")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_l2_default_account_bytecode_hash(self) -> bytes:
        return self._method_("getL2DefaultAccountBytecodeHash")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_pending_governor(self) -> HexStr:
        return self._method_("getPendingGovernor")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_priority_queue_size(self) -> int:
        return self._method_("getPriorityQueueSize")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_proposed_upgrade_hash(self):
        return self._method_("getProposedUpgradeHash")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_proposed_upgrade_timestamp(self):
        return self._method_("getProposedUpgradeTimestamp")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_security_council(self) -> HexStr:
        return self._method_("getSecurityCouncil")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_total_blocks_committed(self) -> int:
        return self._method_("getTotalBlocksCommitted")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_total_blocks_executed(self) -> int:
        return self._method_("getTotalBlocksExecuted")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_total_blocks_verified(self) -> int:
        return self._method_("getTotalBlocksVerified")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_total_priority_txs(self):
        return self._method_('getTotalPriorityTxs')().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_upgrade_proposal_state(self) -> int:
        """
        INFO: it's internal enum type, must be implemented so on python side also
        """
        return self._method_("getUpgradeProposalState")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_verifier(self) -> HexStr:
        return self._method_("getVerifier")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def get_verifier_params(self) -> VerifierParams:
        ret = self._method_("getVerifierParams")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })
        return VerifierParams(ret[0], ret[1], ret[2])

    def get_priority_tx_max_gas_limit(self) -> int:
        return self._method_("getPriorityTxMaxGasLimit")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def is_approved_by_security_council(self) -> bool:
        return self._method_("isApprovedBySecurityCouncil")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def is_diamond_storage_frozen(self) -> bool:
        return self._method_("isDiamondStorageFrozen")().call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def is_eth_withdrawal_finalized(self,
                                    l2_block_number: int,
                                    l2_message_index: int) -> bool:
        return self._method_("isEthWithdrawalFinalized")(l2_block_number,
                                                         l2_message_index).call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def is_facet_freezable(self, facet: HexStr) -> bool:
        return self._method_("isFacetFreezable")(facet).call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def is_function_freezable(self, selector: bytes) -> bool:
        return self._method_("isFunctionFreezable")(selector).call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def request_l2_transaction(self,
                               contract_l2: HexStr,
                               l2_value: int,
                               call_data: bytes,
                               l2_gas_limit: int,
                               l2_gas_per_pubdata_byte_limit: int,
                               factory_deps: List[bytes],
                               refund_recipient: HexStr,
                               gas_price: int,
                               gas_limit: int,
                               l1_value: int) -> TxReceipt:
        nonce = self._nonce()
        tx = self._method_("requestL2Transaction")(contract_l2,
                                                   l2_value,
                                                   call_data,
                                                   l2_gas_limit,
                                                   l2_gas_per_pubdata_byte_limit,
                                                   factory_deps,
                                                   refund_recipient).build_transaction(
            {
                "nonce": nonce,
                'from': self.account.address,
                "gasPrice": gas_price,
                "gas": gas_limit,
                "value": l1_value
            })
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def l2_tx_base_cost(self,
                        gas_price: int,
                        l2_gas_limit: int,
                        l2_gas_per_pubdata_byte_limit: int) -> int:
        return self._method_("l2TransactionBaseCost")(gas_price,
                                                      l2_gas_limit,
                                                      l2_gas_per_pubdata_byte_limit).call(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                'nonce': self._nonce(),
            })

    def parse_events(self, tx_receipt: TxReceipt, event: str):
        return self.contract.events[event]().process_receipt(tx_receipt)
