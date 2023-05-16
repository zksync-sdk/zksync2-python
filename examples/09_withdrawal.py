import os

from eth_account import Account
from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import TxReceipt

from zksync2.core.types import Token
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.provider.eth_provider import EthereumProvider
from zksync2.transaction.transaction_builders import TxWithdraw


def withdraw(
        zksync_provider: Web3, account: LocalAccount, amount: float
) -> HexBytes:
    """Withdraw from Layer 2 to Layer 1 on zkSync network
    :param zksync_provider:
        Instance of ZkSync provider
    :param account:
        From which ETH account the withdrawal will be made
    :param amount:
        How much would the withdrawal will contain
    :return:
         Hash of withdraw transaction on L2 network
    """

    # Create withdrawal transaction
    withdrawal = TxWithdraw(
        web3=zksync_provider,
        token=Token.create_eth(),
        amount=Web3.to_wei(amount, "ether"),
        gas_limit=0,  # unknown
        account=account,
    )

    # ZkSync transaction gas estimation
    estimated_gas = zksync_provider.zksync.eth_estimate_gas(withdrawal.tx)

    # Estimate gas transaction
    tx = withdrawal.estimated_gas(estimated_gas)

    # Sign the transaction
    signed = account.sign_transaction(tx)

    # Broadcast the transaction to the network
    return zksync_provider.zksync.send_raw_transaction(signed.rawTransaction)


def finalize_withdraw(
        zksync_provider: Web3, ethereum_provider: EthereumProvider, withdraw_tx_hash: HexBytes
) -> TxReceipt:
    """
    Execute finalize withdraw transaction on L1 network
    :type zksync_provider:
         Instance of ZkSync provider
    :param ethereum_provider
        Instance of EthereumProvider
    :param withdraw_tx_hash
        Hash of withdraw transaction on L2 network
    :return:
        TxReceipt of finalize withdraw transaction on L1 network
    """
    zks_receipt = zksync_provider.zksync.wait_finalized(withdraw_tx_hash)

    # Check if withdraw transaction was successful
    if not zks_receipt["status"]:
        raise RuntimeError("Withdraw transaction on L2 network failed")

    # Execute finalize withdraw
    tx_receipt = ethereum_provider.finalize_withdrawal(zks_receipt["transactionHash"])

    # Check if finalize withdraw transaction was successful
    if not tx_receipt["status"]:
        raise RuntimeError("Finalize withdraw transaction L1 network failed")
    return tx_receipt


if __name__ == "__main__":
    # Get the private key from OS environment variables
    PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))

    # Set a provider
    ZKSYNC_PROVIDER = "https://testnet.era.zksync.dev"
    ETH_PROVIDER = "https://rpc.ankr.com/eth_goerli"

    # Connect to zkSync network
    zk_web3 = ZkSyncBuilder.build(ZKSYNC_PROVIDER)

    # Connect to Ethereum network
    eth_web3 = Web3(Web3.HTTPProvider(ETH_PROVIDER))
    eth_web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    # Get account object by providing from private key
    account: LocalAccount = Account.from_key(PRIVATE_KEY)

    # Create Ethereum provider
    eth_provider = EthereumProvider(zk_web3, eth_web3, account)

    amount = 0.01

    # Perform the withdrawal
    withdraw_tx_hash = withdraw(zk_web3, account, amount)

    print(f"Withdraw transaction hash: {withdraw_tx_hash.hex()}")
    print("Wait for withdraw transaction to be finalized on L2 network (11-24 hours)")
    print("Read more about withdrawal delay: https://era.zksync.io/docs/dev/troubleshooting/withdrawal-delay.html")
    print("When withdraw transaction is finalized, execute 10_finalize_withdrawal.py script  "
          "with WITHDRAW_TX_HASH environment variable set")
