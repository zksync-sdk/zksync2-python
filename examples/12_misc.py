from eth_account import Account
from eth_account.signers.local import LocalAccount
from examples.utils import EnvPrivateKey
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.core.types import EthBlockParams

ZKSYNC_TEST_URL = "http://127.0.0.1:3050"


def check_balance():
    env = EnvPrivateKey("ZKSYNC_TEST_KEY")
    account: LocalAccount = Account.from_key(env.key)
    zksync_web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    zk_balance = zksync_web3.zksync.get_balance(account.address, EthBlockParams.LATEST.value)
    print(f"ZkSync balance: {zk_balance}")


if __name__ == "__main__":
    check_balance()
