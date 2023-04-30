import os

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from web3 import Web3

from zksync2.core.types import Token
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.transaction.transaction_builders import TxWithdraw


def withdraw_to_l1(zk_web3: ZkSyncBuilder, account: LocalAccount, amount: float) -> HexStr:
    """Withdraw from Layer 2 to Layer 1 on zkSync network
    
    :param zk_web3:
        Instance of ZkSyncBuilder
    
    :param account:
        From which ETH account the withdrawal will be made
    
    :param amount:
        How much would the withdrawal will contain
    
    :return:
        Transaction hash of the withdrawal
    
    """

    # Create withdrawal transaction
    withdrawal = TxWithdraw(web3=zk_web3,
                            token=Token.create_eth(),
                            amount=Web3.to_wei(amount, "ether"),
                            gas_limit=0,  # unknown
                            account=account
                            )
    
    # ZkSync transaction gas estimation
    estimated_gas = zk_web3.zksync.eth_estimate_gas(withdrawal.tx)

    # Estimate gas transaction
    tx = withdrawal.estimated_gas(estimated_gas)
    
    # Sign the transaction
    signed = account.sign_transaction(tx)

    # Broadcast the transaction to the network
    tx_hash = zk_web3.zksync.send_raw_transaction(signed.rawTransaction)

    # Return the transaction hash of the withdrawal
    return tx_hash


if __name__ == "__main__":
    # Get the private key from OS environment variables
    PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))

    # Set a provider
    PROVIDER = "https://zksync2-testnet.zksync.dev"

    # Connect to zkSync network
    zk_web3 = ZkSyncBuilder.build(PROVIDER)

    # Get account object by providing from private key
    account: LocalAccount = Account.from_key(PRIVATE_KEY)

    # Perform the withdraw
    withdraw_to_l1(zk_web3, account, 0.01)





