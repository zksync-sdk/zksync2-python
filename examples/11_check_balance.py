from eth_account import Account
from eth_account.signers.local import LocalAccount
from examples.utils import EnvPrivateKey
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.core.types import EthBlockParams

ZKSYNC_PROVIDER = "https://testnet.era.zksync.dev"


def check_balance():
    env = EnvPrivateKey("PRIVATE_KEY")
    account: LocalAccount = Account.from_key(env.key)
    zksync_web3 = ZkSyncBuilder.build(ZKSYNC_PROVIDER)
    zk_balance = zksync_web3.zksync.get_balance(account.address, EthBlockParams.LATEST.value)
    print(f"Balance: {zk_balance}")


if __name__ == "__main__":
    check_balance()
