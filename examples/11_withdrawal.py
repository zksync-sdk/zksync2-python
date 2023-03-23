from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.middleware import geth_poa_middleware

from zksync2.core.types import Token
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.provider.eth_provider import EthereumProvider
from zksync2.transaction.transaction_builders import TxWithdraw

ZKSYNC_TEST_URL = "http://127.0.0.1:3050"
ETH_TEST_URL = "http://127.0.0.1:8545"
PRIVATE_KEY2 = bytes.fromhex("fd1f96220fa3a40c46d65f81d61dd90af600746fd47e5c82673da937a48b38ef")


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def example_withdrawal(amount: float):
    web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    account: LocalAccount = Account.from_key(PRIVATE_KEY2)

    eth_web3 = Web3(Web3.HTTPProvider(ETH_TEST_URL))
    eth_web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    eth_balance = eth_web3.eth.get_balance(account.address)
    print(f"Eth: balance: {Web3.from_wei(eth_balance, 'ether')}")

    eth_provider = EthereumProvider(web3,
                                    eth_web3,
                                    account)
    withdrawal = TxWithdraw(web3=web3,
                            token=Token.create_eth(),
                            amount=Web3.to_wei(amount, "ether"),
                            gas_limit=0,  # unknown
                            account=account)
    estimated_gas = web3.zksync.eth_estimate_gas(withdrawal.tx)
    tx = withdrawal.estimated_gas(estimated_gas)
    signed = account.sign_transaction(tx)
    tx_hash = web3.zksync.send_raw_transaction(signed.rawTransaction)
    zks_receipt = web3.zksync.wait_finalized(tx_hash, timeout=240, poll_latency=0.5)
    print(f"ZkSync Tx status: {zks_receipt['status']}")
    tx_receipt = eth_provider.finalize_withdrawal(zks_receipt["transactionHash"])
    print(f"Finalize withdrawal, Tx status: {tx_receipt['status']}")

    prev = eth_balance
    eth_balance = eth_web3.eth.get_balance(account.address)
    print(f"Eth: balance: {Web3.from_wei(eth_balance, 'ether')}")

    fee = tx_receipt['gasUsed'] * tx_receipt['effectiveGasPrice']
    withdraw_absolute = Web3.to_wei(amount, 'ether') - fee
    diff = eth_balance - prev
    if withdraw_absolute == diff:
        print(f"{Colors.OKGREEN}Withdrawal including tx fee is passed{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Eth diff with fee included: {Web3.from_wei(diff, 'ether')}{Colors.ENDC}")
    else:
        print(f"P{Colors.FAIL}Withdrawal failed{Colors.ENDC}")
        print(f"{Colors.FAIL}Eth diff with fee included: {Web3.from_wei(diff, 'ether')}{Colors.ENDC}")


if __name__ == "__main__":
    example_withdrawal(0.1)
