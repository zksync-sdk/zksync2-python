import importlib.resources as pkg_resources
from eth_account.signers.base import BaseAccount
from web3 import Web3
from web3.contract import Contract
from eth_typing import HexStr

from typing import List
import json
from .. import contract_abi

l1_eth_bridge_abi_cache = None


def _l1_eth_bridge_abi_default():
    global l1_eth_bridge_abi_cache

    if l1_eth_bridge_abi_cache is None:
        with pkg_resources.path(contract_abi, "L1EthBridge.json") as p:
            with p.open(mode='r') as json_file:
                data = json.load(json_file)
                l1_eth_bridge_abi_cache = data['abi']
    return l1_eth_bridge_abi_cache


class L1EthBridge:
    DEFAULT_GAS_LIMIT = 21000

    def __init__(self, contract_address: HexStr, web3: Web3, eth_account: BaseAccount, abi=None):
        check_sum_address = Web3.toChecksumAddress(contract_address)
        self.web3 = web3
        self.addr = check_sum_address
        self.account = eth_account
        if abi is None:
            abi = _l1_eth_bridge_abi_default()
        self.contract: Contract = self.web3.eth.contract(self.addr, abi=abi)

    def _get_nonce(self):
        return self.web3.eth.get_transaction_count(self.account.address)

    def claim_failed_deposit(self, deposit_sender: HexStr,
                             l1_token: HexStr,
                             tx_hash: bytes,
                             l2_block_number: int,
                             l2_msg_index: int,
                             merkle_proof: List[bytes]):
        tx = self.contract.functions.claimFailedDeposit(deposit_sender,
                                                        l1_token,
                                                        tx_hash,
                                                        l2_block_number,
                                                        l2_msg_index,
                                                        merkle_proof).build_transaction(
            {
                "chainId": self.web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self._get_nonce(),
                "gas": self.DEFAULT_GAS_LIMIT,
                "gasPrice": self.web3.eth.gas_price
            })
        signed_tx = self.account.sign_transaction(tx)
        txn_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)
        return txn_receipt

    def deposit(self, l2_receiver: HexStr, l1_token: HexStr, amount: int):
        tx = self.contract.functions.deposit(l2_receiver,
                                             l1_token,
                                             amount).build_transaction(
            {
                "chainId": self.web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self._get_nonce(),
                "gas": self.DEFAULT_GAS_LIMIT,
                "gasPrice": self.web3.eth.gas_price,
                "value": amount
            })
        signed_tx = self.account.sign_transaction(tx)
        txn_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)
        return txn_receipt

    def finalize_withdrawal(self,
                            l2_block_number: int,
                            l2_msg_index: int,
                            msg: bytes,
                            merkle_proof: List[bytes]):
        tx = self.contract.functions.finalizeWithdrawal(l2_block_number,
                                                        l2_msg_index,
                                                        msg,
                                                        merkle_proof).build_transaction(
            {
                "chainId": self.web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self._get_nonce(),
                "gas": self.DEFAULT_GAS_LIMIT,
                "gasPrice": self.web3.eth.gas_price
            })
        signed_tx = self.account.sign_transaction(tx)
        txn_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)
        return txn_receipt

    def initialize(self, l2_bridge_bytecode: bytes):
        tx_hash = self.contract.functions.initialize(l2_bridge_bytecode).transact()
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def is_withdrawal_finalized(self) -> bool:
        return self.contract.functions.isWithdrawalFinalized().call()

    def l2_bridge(self) -> HexStr:
        return self.contract.functions.l2Bridge().call()

    def l2_token_address(self, l1_token: HexStr):
        return self.contract.functions.l2TokenAddress(l1_token).call()

    @property
    def address(self):
        return self.addr
