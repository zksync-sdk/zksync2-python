from decimal import Decimal
from typing import Optional

from eth_account.signers.base import BaseAccount
from eth_typing import HexStr
from web3 import Web3
from zksync2.manage_contracts.erc20_contract import ERC20Contract
from zksync2.manage_contracts.gas_provider import GasProvider
from zksync2.manage_contracts.l1_bridge import L1Bridge
from zksync2.manage_contracts.priority_op_tree import PriorityOpTree
from zksync2.manage_contracts.priority_queue_type import PriorityQueueType
from zksync2.manage_contracts.zksync_contract import ZkSyncContract
from zksync2.core.types import Token, ADDRESS_DEFAULT, BridgeAddresses


class EthereumProvider:
    GAS_LIMIT = 21000
    DEFAULT_THRESHOLD = 2 ** 255

    def __init__(self,
                 web3: Web3,
                 erc20_bridge: L1Bridge,
                 eth_bridge: L1Bridge,
                 account: BaseAccount,
                 zksync: Optional[ZkSyncContract] = None):
        self.web3 = web3
        self.account = account
        self.l1_erc20_bridge = erc20_bridge
        self.l1_eth_bridge = eth_bridge
        self.zksync_contract = zksync

    @classmethod
    def build_ethereum_provider(cls, zksync: Web3, eth: Web3, account: BaseAccount, gas_provider: GasProvider):
        bridge_contracts: BridgeAddresses = zksync.zksync.zks_get_bridge_contracts()
        erc20_bridge = L1Bridge(bridge_contracts.l1_erc20_default_bridge, eth, account, gas_provider)
        eth_bridge = L1Bridge(bridge_contracts.l1_eth_default_bridge, eth, account, gas_provider)
        provider = cls(web3=eth,
                       erc20_bridge=erc20_bridge,
                       eth_bridge=eth_bridge,
                       account=account)
        return provider

    def approve_deposits(self, token: Token, limit: Optional[int]):
        token_contract = ERC20Contract(self.web3,
                                       token.l1_address,
                                       self.account)
        if limit is None:
            return token_contract.approve_deposit(self.l1_erc20_bridge.contract.address)
        return token_contract.approve_deposit(self.l1_erc20_bridge.contract.address, limit)

    def transfer(self, token: Token, amount: Decimal, to: HexStr):
        if token.is_eth():
            tx = {
                'nonce': self.web3.eth.get_transaction_count() + 1,
                'to': to,
                'value': Web3.toWei(amount, 'ether'),
                'gas': self.GAS_LIMIT,
                'gasPrice': self.web3.eth.gas_price
            }
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.account)
            return self.web3.eth.send_raw_transaction(signed_tx)
        else:
            token_contract = ERC20Contract(web3=self.web3,
                                           contract_address=token.l1_address,
                                           account=self.account)
            return token_contract.transfer(to, token.to_int(amount))

    def get_deposit_base_cost(self, gas_price: int = None):
        if gas_price is None:
            return self.web3.eth.gas_price
        return self.zksync_contract.deposit_base_cost(gas_price,
                                                      PriorityQueueType.DEQUE.value,
                                                      PriorityOpTree.FULL.value)

    def deposit(self, token: Token, amount: int, user_address: HexStr):
        if token.is_eth():
            return self.l1_eth_bridge.deposit(user_address, ADDRESS_DEFAULT, amount)
        return self.l1_erc20_bridge.deposit(user_address, token.l1_address, amount)

    def withdraw(self, token: Token, amount: int, user_address: str):
        raise NotImplementedError("Unsupported operation")

    def is_deposit_approved(self, token: Token, to: HexStr, threshold: int = DEFAULT_THRESHOLD):
        token_contract = ERC20Contract(self.web3, token.l1_address, self.account)
        ret = token_contract.allowance(to, self.l1_erc20_bridge.address)
        return ret >= threshold
