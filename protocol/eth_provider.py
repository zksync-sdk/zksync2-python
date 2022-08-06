# from decimal import Decimal
# from typing import Optional

from decimal import Decimal

from eth_typing import HexStr
from web3 import Web3
from protocol.erc20_contract import ERC20Contract
from protocol.zksync_contract import ZkSyncContract
from zk_types.zk_types import Token
from zk_types.priority_queue_type import PriorityQueueType
from zk_types.priority_op_tree import PriorityOpTree


# TODO: check to use Static Gas provider for ZkSync

class EthereumProvider:
    # gas - gas limit - amount of iteration code  execution
    # gas price = price of 1 gas limit

    GAS_LIMIT = 21000

    def __init__(self, web3: Web3, zksync: ZkSyncContract):
        self.web3 = web3
        self.zksync_contract = zksync

    @property
    def address(self):
        return self.zksync_contract.contract_address

    def approve_deposits(self, token: Token, limit: Decimal):
        contract = ERC20Contract(self.web3,
                                 # self.zksync_contract.contract_address,
                                 # self.address,
                                 token.address,
                                 self.zksync_contract.account)
        # return contract.approve_deposit(token.to_int(limit))
        return contract.approve_deposit(self.address, token.to_int(limit))

    def transfer(self, token: Token, amount: Decimal, to: HexStr):
        if token.is_eth():
            tx = {
                'nonce': self.web3.eth.get_transaction_count() + 1,
                'to': to,
                'value': Web3.toWei(amount, 'ether'),
                'gas': self.GAS_LIMIT,
                'gasPrice': self.web3.eth.gas_price
            }
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.zksync_contract.account)
            return self.web3.eth.send_raw_transaction(signed_tx)
        else:
            # token_contract = ERC20Contract(web3=self.web3,
            #                                zksync_address=token.address,
            #                                contract_address=self.zksync_contract.contract_address,
            #                                account=self.zksync_contract.account)
            # return token_contract.transfer(to, token.to_int(amount))
            token_contract = ERC20Contract(web3=self.web3,
                                           contract_address=token.address,
                                           account=self.zksync_contract.account)
            return token_contract.transfer(to, token.to_int(amount))

    def get_deposit_base_cost(self, gas_price: int = None):
        if gas_price is None:
            return self.web3.eth.gas_price
        return self.zksync_contract.deposit_base_cost(gas_price,
                                                      PriorityQueueType.DEQUE.value,
                                                      PriorityOpTree.FULL.value)

    def deposit(self, token: Token, amount: int, user_address: str):
        base_cost = self.get_deposit_base_cost()
        value = base_cost + amount
        if token.is_eth():
            return self.zksync_contract.deposit_eth(amount,
                                                    user_address,
                                                    PriorityQueueType.DEQUE.value,
                                                    PriorityOpTree.FULL.value, value)
        else:
            # USE ZKSYNC to_int
            return self.zksync_contract.deposit_erc20(token.address,
                                                      amount,
                                                      user_address,
                                                      PriorityQueueType.DEQUE.value,
                                                      PriorityOpTree.FULL.value)

    def withdraw(self, token: Token, amount: int, user_address: str):
        return self.zksync_contract.request_withdraw(token.address, amount, user_address,
                                                     PriorityQueueType.DEQUE.value,
                                                     PriorityOpTree.FULL.value)

    def is_deposit_approved(self, token: Token, to: str, threshold: int = None):
        # token_contract = ERC20Contract(self.web3, self.address, token.address,
        #                                self.zksync_contract.account)
        # # TODO: refactor it
        # if threshold is not None:
        #     return token_contract.is_deposit_approved(to, threshold)
        # else:
        #     return token_contract.is_deposit_approved(to)

        token_contract = ERC20Contract(self.web3, token.address, self.zksync_contract.account)
        # TODO: refactor it
        if threshold is not None:
            return token_contract.is_deposit_approved(self.zksync_contract.contract_address, to, threshold)
        else:
            return token_contract.is_deposit_approved(self.zksync_contract.contract_address, to)
