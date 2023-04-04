from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

from examples.utils import EnvPrivateKey
from zksync2.core.types import Token, EthBlockParams
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.provider.eth_provider import EthereumProvider

# ZKSYNC_TEST_URL = "http://127.0.0.1:3050"
# ETH_TEST_URL = "http://127.0.0.1:8545"
ZKSYNC_TEST_URL = "https://zksync2-testnet.zksync.dev"
ETH_TEST_URL = "https://rpc.ankr.com/eth_goerli"


def deposit(amount: float):
    env = EnvPrivateKey("ZKSYNC_TEST_KEY")
    zksync = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    eth_web3 = Web3(Web3.HTTPProvider(ETH_TEST_URL))
    account: LocalAccount = Account.from_key(env.key())
    eth_provider = EthereumProvider(zksync, eth_web3, account)
    wei_amount = Web3.to_wei(amount, "ether")
    eth_token = Token.create_eth()
    gas_price = eth_web3.eth.gas_price
    before_deposit = eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)

    print(f"Before: {before_deposit}")
    l1_tx_receipt = eth_provider.deposit(token=Token.create_eth(),
                                         amount=wei_amount,
                                         gas_price=gas_price)
    # TODO: when L2 tx

    after = eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
    print(f"After : {after}")

    print(f"Tx status: {l1_tx_receipt['status']}")


if __name__ == "__main__":
    deposit(0.1)
