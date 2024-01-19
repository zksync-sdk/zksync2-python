#Deposits token to l2 so that tests can run
import json
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

from zksync2.account.wallet import Wallet
from zksync2.core.types import DepositTransaction
from zksync2.manage_contracts.utils import zksync_abi_default
from zksync2.module.module_builder import ZkSyncBuilder


def main():
    zksync = ZkSyncBuilder.build("http://127.0.0.1:3050")
    eth_web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    account: LocalAccount = Account.from_key("0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110")
    wallet = Wallet(zksync, eth_web3, account)
    zksync_contract = eth_web3.eth.contract(
        Web3.to_checksum_address(zksync.zksync.main_contract_address),
        abi=zksync_abi_default())

    deposit_token(wallet, eth_web3, zksync, zksync_contract)

def deposit_token(wallet: Wallet, eth_web3: Web3, zksync: Web3, zksync_contract):
    amount = 50
    l1_address = load_token()

    tx_hash = wallet.deposit(DepositTransaction(Web3.to_checksum_address(l1_address),
                                                amount,
                                                wallet.address,
                                                approve_erc20=True,
                                                refund_recipient=wallet.address))

    l1_tx_receipt = eth_web3.eth.wait_for_transaction_receipt(tx_hash)

    l2_hash = zksync.zksync.get_l2_hash_from_priority_op(l1_tx_receipt, zksync_contract)
    zksync.zksync.wait_for_transaction_receipt(transaction_hash=l2_hash,
                                               timeout=360,
                                               poll_latency=10)


def load_token():
    directory = Path(__file__).parent.parent
    path = directory / "tests/integration/token.json"

    with open(path, 'r') as file:
        data = json.load(file)
    return data[0]["address"]


if __name__ == "__main__":
    main()