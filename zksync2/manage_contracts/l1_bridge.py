import json
import importlib.resources as pkg_resources
from eth_account.signers.base import BaseAccount
from web3 import Web3
from web3.contract import Contract
from eth_typing import HexStr
from typing import List, Optional
from web3.types import TxReceipt
from zksync2.manage_contracts.contract_encoder_base import BaseContractEncoder
from zksync2.manage_contracts import contract_abi

l1_bridge_abi_cache = None


def _l1_bridge_abi_default():
    global l1_bridge_abi_cache

    if l1_bridge_abi_cache is None:
        with pkg_resources.path(contract_abi, "IL1Bridge.json") as p:
            with p.open(mode='r') as json_file:
                data = json.load(json_file)
                l1_bridge_abi_cache = data['abi']
    return l1_bridge_abi_cache


class L1Bridge:
    def __init__(self,
                 contract_address: HexStr,
                 web3: Web3,
                 eth_account: BaseAccount,
                 # gas_provider: GasProvider,
                 abi=None):
        check_sum_address = Web3.to_checksum_address(contract_address)
        self.web3 = web3
        self.addr = check_sum_address
        self.account = eth_account
        # self.gas_provider = gas_provider
        if abi is None:
            abi = _l1_bridge_abi_default()
        self.contract: Contract = self.web3.eth.contract(self.addr, abi=abi)

    def _get_nonce(self):
        return self.web3.eth.get_transaction_count(self.account.address)

    def claim_failed_deposit(self,
                             deposit_sender: HexStr,
                             l1_token: HexStr,
                             l2tx_hash: bytes,
                             l2_block_number: int,
                             l2_msg_index: int,
                             l2_tx_number_in_block: int,
                             merkle_proof: List[bytes]):
        params = {
            "chainId": self.web3.eth.chain_id,
            "from": self.account.address,
            "nonce": self._get_nonce()
        }
        self.contract.functions.claimFailedDeposit(deposit_sender,
                                                   l1_token,
                                                   l2tx_hash,
                                                   l2_block_number,
                                                   l2_msg_index,
                                                   l2_tx_number_in_block,
                                                   merkle_proof).call(params)

    def deposit(self,
                l2_receiver: HexStr,
                l1_token: HexStr,
                amount: int,
                l2_tx_gas_limit: int,
                l2_tx_gas_per_pubdata_byte: int) -> TxReceipt:
        tx = self.contract.functions.deposit(l2_receiver,
                                             l1_token,
                                             amount,
                                             l2_tx_gas_limit,
                                             l2_tx_gas_per_pubdata_byte
                                             ).build_transaction(
            {
                "chainId": self.web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self._get_nonce(),
                # "gas": self.gas_provider.gas_limit(),
                # "gasPrice": self.gas_provider.gas_price(),
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
                            merkle_proof: List[bytes]) -> TxReceipt:
        tx = self.contract.functions.finalizeWithdrawal(l2_block_number,
                                                        l2_msg_index,
                                                        msg,
                                                        merkle_proof).build_transaction(
            {
                "chainId": self.web3.eth.chain_id,
                "from": self.account.address,
                "nonce": self._get_nonce(),
                # "gas": self.gas_provider.gas_limit(),
                # "gasPrice": self.gas_provider.gas_price()
            })
        signed_tx = self.account.sign_transaction(tx)
        txn_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash)
        return txn_receipt

    def is_withdrawal_finalized(self, l2_block_number: int, l2_msg_index: int) -> bool:
        return self.contract.functions.isWithdrawalFinalized(l2_block_number, l2_msg_index).call()

    def l2_token_address(self, l1_token: HexStr) -> HexStr:
        return self.contract.functions.l2TokenAddress(l1_token).call()

    @property
    def address(self):
        return self.contract.address


class L1BridgeEncoder(BaseContractEncoder):

    def __init__(self, web3: Web3, abi: Optional[dict] = None):
        if abi is None:
            abi = _l1_bridge_abi_default()
        super(L1BridgeEncoder, self).__init__(web3, abi)
