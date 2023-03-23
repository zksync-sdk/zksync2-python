from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.core.types import EthBlockParams

ZKSYNC_TEST_URL = "http://127.0.0.1:3050"
PRIVATE_KEY2 = bytes.fromhex("fd1f96220fa3a40c46d65f81d61dd90af600746fd47e5c82673da937a48b38ef")


def check_balance():
    account: LocalAccount = Account.from_key(PRIVATE_KEY2)
    zksync_web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    zk_balance = zksync_web3.zksync.get_balance(account.address, EthBlockParams.LATEST.value)
    print(f"ZkSync balance: {zk_balance}")


if __name__ == "__main__":
    check_balance()
