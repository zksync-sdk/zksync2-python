from web3 import Web3
from web3.contract import Contract
from eth_typing import HexStr

from pathlib import Path
from typing import List
import json

l1_erc20_bridge_abi_cache = None
l1_erc20_bridge_abi_default_path = Path('./contract_abi/L1ERC20Bridge.json')


def _l1_erc20_bridge_abi_default():
    global l1_erc20_bridge_abi_cache

    if l1_erc20_bridge_abi_cache is None:
        with l1_erc20_bridge_abi_default_path.open(mode='r') as json_file:
            data = json.load(json_file)
            l1_erc20_bridge_abi_cache = data['abi']
    return l1_erc20_bridge_abi_cache


class L1ERC20Bridge:

    def __init__(self, contract_address: HexStr, web3: Web3, abi=None):
        check_sum_address = Web3.toChecksumAddress(contract_address)
        self.web3 = web3
        self.addr = check_sum_address
        if abi is None:
            abi = _l1_erc20_bridge_abi_default()
        self.contract: Contract = self.web3.eth.contract(self.addr, abi=abi)

    def claim_failed_deposit(self, deposit_sender: HexStr,
                             l1_token: HexStr,
                             tx_hash,
                             l2_block_number: int,
                             l2_msg_index: int,
                             merkle_proof: List[bytes]):
        tx_hash = self.contract.functions.claimFailedDeposit(deposit_sender,
                                                             l1_token,
                                                             tx_hash,
                                                             l2_block_number,
                                                             l2_msg_index,
                                                             merkle_proof).transact()
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def deposit(self, l2_receiver: HexStr, l1_token: HexStr, amount: int, queue_type: int):
        tx_hash = self.contract.functions.deposit(l2_receiver, l1_token, amount, queue_type).transact()
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def finalize_withdrawal(self,
                            l2_block_number: int,
                            l2_msg_index: int,
                            msg: bytes,
                            merkle_proof: List[bytes]):
        tx_hash = self.contract.functions.finalizeWithdrawal(l2_block_number, l2_msg_index, msg, merkle_proof).transact()
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def initialize(self,
                   l2_bridge_bytecode: bytes,
                   l2_standard_erc20_bytecode: bytes):
        tx_hash = self.contract.functions.initialize(l2_bridge_bytecode, l2_standard_erc20_bytecode).transact()
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def l2_bridge(self):
        return self.contract.functions.l2Bridge().call()

    def l2_standard_erc20_bytecode_hash(self):
        return self.contract.functions.l2StandardERC20BytecodeHash().call()

    def l2_token_address(self, l1_token: HexStr):
        return self.contract.functions.l2TokenAddress(l1_token).call()

