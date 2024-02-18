from zksync2.account.wallet_l1 import WalletL1
from zksync2.account.wallet_l2 import WalletL2

from web3 import Web3

from eth_account.signers.base import BaseAccount


class Wallet(WalletL1, WalletL2):
    def __init__(self, zksync_web3: Web3, eth_web3: Web3, l1_account: BaseAccount):
        self._eth_web3 = eth_web3
        self._zksync_web3 = zksync_web3
        self._l1_account = l1_account
        WalletL1.__init__(self, zksync_web3, eth_web3, l1_account)
        WalletL2.__init__(self, zksync_web3, eth_web3, l1_account)

    def sign_transaction(self, tx):
        return self._l1_account.sign_transaction(tx)
