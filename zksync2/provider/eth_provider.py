from typing import Union, List

from eth_account.signers.base import BaseAccount
from eth_typing import HexStr
from eth_utils import event_signature_to_log_topic, add_0x_prefix
from eth_abi.codec import *

from web3 import Web3
from web3.types import TxReceipt

from zksync2.core.utils import RecommendedGasLimit, to_bytes, is_eth
from zksync2.manage_contracts.erc20_contract import ERC20Contract
from zksync2.manage_contracts.l1_bridge import L1Bridge
from zksync2.manage_contracts.l2_bridge import L2Bridge
from zksync2.manage_contracts.zksync_contract import ZkSyncContract
from zksync2.core.types import Token, BridgeAddresses, EthBlockParams, ZksMessageProof


def check_base_cost(base_cost: int, value: int):
    if base_cost > value:
        raise RuntimeError(f"The base cost of performing the priority operation is higher than"
                           f" the provided value parameter"
                           f" for the transaction: base_cost: ${base_cost},"
                           f" provided value: ${value}`")


class EthereumProvider:
    # GAS_LIMIT = 21000
    # DEFAULT_THRESHOLD = 2 ** 255
    DEPOSIT_GAS_PER_PUBDATA_LIMIT = 800
    RECOMMENDED_DEPOSIT_L2_GAS_LIMIT = 10000000
    L1_MESSENGER_ADDRESS = '0x0000000000000000000000000000000000008008'

    def __init__(self,
                 zksync_web3: Web3,
                 eth_web3: Web3,
                 l1_account: BaseAccount):
        self._eth_web3 = eth_web3
        self._zksync_web3 = zksync_web3
        self._main_contract_address = self._zksync_web3.zksync.zks_main_contract()
        self._l1_account = l1_account
        self._main_contract = ZkSyncContract(zksync_main_contract=self._main_contract_address,
                                             eth=self._eth_web3,
                                             account=l1_account)
        bridge_addresses: BridgeAddresses = self._zksync_web3.zksync.zks_get_bridge_contracts()
        self._l1_bridge = L1Bridge(bridge_addresses.erc20_l1_default_bridge,
                                   self._eth_web3, l1_account)

    @property
    def main_contract(self):
        return self._main_contract

    @property
    def l1_bridge(self):
        return self._l1_bridge

    @property
    def address(self):
        return self._l1_account.address

    def get_l1_balance(self, token: Token, block: EthBlockParams):
        if token.is_eth():
            return self._eth_web3.eth.get_balance(self.address, block.value)
        else:
            token_contract = ERC20Contract(self._eth_web3.eth,
                                           token.l1_address,
                                           self._l1_account)
            return token_contract.balance_of(self.address)

    def l2_token_address(self, token: Token):
        if token.is_eth():
            return token.l1_address
        else:
            return self.l1_bridge.l2_token_address(token.l1_address)

    def get_base_cost(self,
                      l2_gas_limit: int,
                      gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT,
                      gas_price: int = None):
        if gas_price is None:
            gas_price = self._eth_web3.eth.gas_price
        return self.main_contract.l2_tx_base_cost(gas_price, l2_gas_limit, gas_per_pubdata_byte)

    def approve_erc20(self,
                      token: Token,
                      amount: int,
                      bridge_address: HexStr = None,
                      gas_limit: int = None) -> TxReceipt:
        if token.is_eth():
            raise RuntimeError("ETH token can't be approved. The address of the token does not exist on L1")

        erc20 = ERC20Contract(self._eth_web3.eth, token.l1_address, self._l1_account)
        if bridge_address is None:
            bridge_address = self._l1_bridge.address

        if gas_limit is None:
            # TODO: get the approve(bridgeAddress, amount) estimateGas transaction to put correct gas_limit
            gas_limit = RecommendedGasLimit.ERC20_APPROVE

        return erc20.approve(bridge_address, amount, gas_limit)

    def deposit(self,
                token: Token,
                amount: int,
                to: HexStr = None,
                operator_tip: int = 0,
                bridge_address: HexStr = None,
                approve_erc20: bool = False,
                l2_gas_limit: int = RecommendedGasLimit.DEPOSIT.value,
                gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT,
                gas_price: int = None,
                gas_limit: int = None
                ):
        bridge_contract = self.l1_bridge
        if bridge_address is not None:
            bridge_contract = L1Bridge(bridge_address,
                                       self._eth_web3,
                                       self._l1_account)

        if to is None:
            to = self.address

        if gas_price is None:
            gas_price = self._eth_web3.eth.gas_price
        if gas_limit is None:
            gas_limit = RecommendedGasLimit.DEPOSIT.value

        base_cost = self.get_base_cost(gas_price=gas_price,
                                       gas_per_pubdata_byte=gas_per_pubdata_byte,
                                       l2_gas_limit=l2_gas_limit)

        if token.is_eth():
            value = base_cost + operator_tip + amount
            return self.request_execute(
                contract_address=to,
                call_data=HexStr("0x"),
                l2_gas_limit=l2_gas_limit,
                l2_value=amount,
                gas_per_pubdata_byte=gas_per_pubdata_byte,
                gas_price=gas_price,
                gas_limit=gas_limit,
                l1_value=value)
        else:
            value = base_cost + operator_tip
            check_base_cost(base_cost, value)

            if approve_erc20:
                self.approve_erc20(token,
                                   amount,
                                   bridge_address,
                                   gas_limit)
            tx_receipt = bridge_contract.deposit(l2_receiver=to,
                                                 l1_token=token.l1_address,
                                                 amount=amount,
                                                 l2_tx_gas_limit=l2_gas_limit,
                                                 l2_tx_gas_per_pubdata_byte=gas_per_pubdata_byte)
            return tx_receipt

    def request_execute(self,
                        contract_address: HexStr,
                        call_data: Union[bytes, HexStr],
                        l2_gas_limit: int,
                        l1_value: int,
                        l2_value: int = 0,
                        factory_deps: List[bytes] = None,
                        operator_tip: int = 0,
                        gas_per_pubdata_byte: int = DEPOSIT_GAS_PER_PUBDATA_LIMIT,
                        refund_recipient: HexStr = None,
                        gas_price: int = None,
                        gas_limit: int = RecommendedGasLimit.EXECUTE.value):

        if factory_deps is None:
            factory_deps = list()
        if refund_recipient is None:
            refund_recipient = self.address
        if gas_price is None:
            gas_price = self._eth_web3.eth.gas_price

        base_cost = self.get_base_cost(gas_price=gas_price,
                                       gas_per_pubdata_byte=gas_per_pubdata_byte,
                                       l2_gas_limit=l2_gas_limit)
        value = base_cost + operator_tip + l2_value
        check_base_cost(base_cost, value)

        call_data = to_bytes(call_data)

        tx_receipt = self.main_contract.request_l2_transaction(contract_l2=contract_address,
                                                               l2_value=l2_value,
                                                               call_data=call_data,
                                                               l2_gas_limit=l2_gas_limit,
                                                               l2_gas_per_pubdata_byte_limit=gas_per_pubdata_byte,
                                                               factory_deps=factory_deps,
                                                               refund_recipient=refund_recipient,
                                                               gas_price=gas_price,
                                                               gas_limit=gas_limit,
                                                               l1_value=l1_value)
        return tx_receipt

    def _get_withdraw_log(self, tx_receipt: TxReceipt, index: int = 0):
        topic = event_signature_to_log_topic("L1MessageSent(address,bytes32,bytes)")

        def impl_filter(log):
            return log['address'] == self.L1_MESSENGER_ADDRESS and \
                   log['topics'][0] == topic

        filtered_logs = list(filter(impl_filter, tx_receipt['logs']))
        return filtered_logs[index], int(tx_receipt['l1BatchTxIndex'], 16)

    def _get_withdraw_l2_to_l1_log(self, tx_receipt: TxReceipt, index: int = 0):
        msgs = []
        for i, e in enumerate(tx_receipt['l2ToL1Logs']):
            if e["sender"].lower() == self.L1_MESSENGER_ADDRESS.lower():
                msgs.append((i, e))
        l2_to_l1_log_index, log = msgs[index]
        return l2_to_l1_log_index, log

    def _finalize_withdrawal_params(self, withdraw_hash, index: int) -> dict:
        tx_receipt = self._zksync_web3.zksync.get_transaction_receipt(withdraw_hash)
        log, l1_batch_tx_id = self._get_withdraw_log(tx_receipt, index)
        l2_to_l1_log_index, _ = self._get_withdraw_l2_to_l1_log(tx_receipt, index)
        sender = add_0x_prefix(HexStr(log['topics'][1][12:].hex()))
        hex_hash = withdraw_hash.hex()
        proof: ZksMessageProof = self._zksync_web3.zksync.zks_get_log_proof(hex_hash, l2_to_l1_log_index)
        bytes_data = to_bytes(log['data'])
        msg = self._zksync_web3.codec.decode(["bytes"], bytes_data)[0]
        l1_batch_number = int(log['l1BatchNumber'], 16)

        return {
            "l1_batch_number": l1_batch_number,
            "l2_message_index": proof.id,
            "l2_tx_number_in_block": l1_batch_tx_id,
            "message": msg,
            "sender": sender,
            "proof": proof.proof
        }

    def finalize_withdrawal(self, withdraw_hash, index: int = 0):
        params = self._finalize_withdrawal_params(withdraw_hash, index)
        merkle_proof = []
        for proof in params["proof"]:
            merkle_proof.append(to_bytes(proof))

        if is_eth(params["sender"]):
            return self.main_contract.finalize_eth_withdrawal(
                l2_block_number=params["l1_batch_number"],
                l2_message_index=params["l2_message_index"],
                l2_tx_number_in_block=params["l2_tx_number_in_block"],
                message=params["message"],
                merkle_proof=merkle_proof)
        else:
            # TODO: check should it be different account for L1/L2
            l2bridge = L2Bridge(contract_address=params["sender"],
                                web3_zks=self._zksync_web3,
                                zksync_account=self._l1_account)
            l1bridge = L1Bridge(contract_address=l2bridge.l1_bridge(),
                                web3=self._eth_web3,
                                eth_account=self._l1_account)
            return l1bridge.finalize_withdrawal(l2_block_number=params["l1_batch_number"],
                                                l2_msg_index=params["l2_message_index"],
                                                msg=params["message"],
                                                merkle_proof=merkle_proof)

    def is_withdrawal_finalized(self, withdraw_hash, index: int = 0):
        tx_receipt = self._zksync_web3.zksync.get_transaction_receipt(withdraw_hash)
        log, _ = self._get_withdraw_log(tx_receipt, index)
        l2_to_l1_log_index = self._get_withdraw_l2_to_l1_log(tx_receipt, index)
        sender = add_0x_prefix(HexStr(log.topics[1][12:].hex()))
        hex_hash = withdraw_hash.hex()
        proof: ZksMessageProof = self._zksync_web3.zksync.zks_get_log_proof(hex_hash, l2_to_l1_log_index)

        l2_block_number = log["l1BatchNumber"]
        if is_eth(sender):
            return self.main_contract.is_eth_withdrawal_finalized(
                l2_block_number=l2_block_number,
                l2_message_index=proof.id)
        else:
            # TODO: check should it be different account for L1/L2
            l2bridge = L2Bridge(contract_address=sender,
                                web3_zks=self._zksync_web3,
                                zksync_account=self._l1_account)
            l1bridge = L1Bridge(contract_address=l2bridge.l1_bridge(),
                                web3=self._eth_web3,
                                eth_account=self._l1_account)
            return l1bridge.is_withdrawal_finalized(l2_block_number=l2_block_number,
                                                    l2_msg_index=proof.id)
