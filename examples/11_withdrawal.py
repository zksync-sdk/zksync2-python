import os

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from web3 import Web3

from zksync2.core.types import Token
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.transaction.transaction_builders import TxWithdraw


def withdraw_to_l1(zk_web3: ZkSyncBuilder, account: LocalAccount, amount: float) -> HexStr:

    withdrawal = TxWithdraw(web3=zk_web3,
                            token=Token.create_eth(),
                            amount=Web3.to_wei(amount, "ether"),
                            gas_limit=0,  # unknown
                            account=account
                            )
    

    estimated_gas = zk_web3.zksync.eth_estimate_gas(withdrawal.tx)


    tx = withdrawal.estimated_gas(estimated_gas)
    

    signed = account.sign_transaction(tx)

    tx_hash = zk_web3.zksync.send_raw_transaction(signed.rawTransaction)

    return tx_hash


if __name__ == "__main__":

    PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))

    PROVIDER = "https://zksync2-testnet.zksync.dev"


    zk_web3 = ZkSyncBuilder.build(PROVIDER)


    account: LocalAccount = Account.from_key(PRIVATE_KEY)

    withdraw_to_l1(zk_web3, account, 0.01)





