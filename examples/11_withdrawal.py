import os

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import TxReceipt

from zksync2.core.types import Token
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.provider.eth_provider import EthereumProvider
from zksync2.transaction.transaction_builders import TxWithdraw


def withdraw(
        zksync_provider: Web3, account: LocalAccount, amount: float
) -> TxReceipt:
    """Withdraw from Layer 2 to Layer 1 on zkSync network
    :param zksync_provider:
        Instance of ZkSync provider
    :param account:
        From which ETH account the withdrawal will be made
    :param amount:
        How much would the withdrawal will contain
    :return:
        Transaction receipt of the withdrawal
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
    tx_hash = zksync_provider.zksync.send_raw_transaction(signed.rawTransaction)

    # Wait for the transaction to be finalized
    zks_receipt = zksync_provider.zksync.wait_finalized(tx_hash, timeout=240, poll_latency=0.5)

    # Check if transaction was successful
    if not zks_receipt["status"]:
        raise RuntimeError("Withdraw transaction on L2 network failed")

    # Return the transaction receipt of the withdrawal
    return zks_receipt


def finalize_withdraw(
        ethereum_provider: EthereumProvider, zks_receipt: TxReceipt
) -> TxReceipt:
    """
    Execute finalize withdraw transaction on L1 network
    :param ethereum_provider
        Instance of EthereumProvider
    :param zks_receipt
        TxReceipt of withdraw transaction on L2 network
    :return:
        TxReceipt of finalize withdraw transaction on L1 network
    """
    tx_receipt = ethereum_provider.finalize_withdrawal(zks_receipt["transactionHash"])
    if not tx_receipt["status"]:
        raise RuntimeError("Finalize withdraw transaction L1 network failed")
    return tx_receipt


if __name__ == "__main__":
    # Get the private key from OS environment variables
    PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))

    # Set a provider
    ZKSYNC_PROVIDER = "https://zksync2-testnet.zksync.dev"
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

    # Perform the withdrawal
    amount = 0.01
    zks_tx_receipt = withdraw(zk_web3, account, amount)
    eth_tx_receipt = finalize_withdraw(eth_provider, zks_tx_receipt)
    fee = eth_tx_receipt["gasUsed"] * eth_tx_receipt["effectiveGasPrice"]

    print(f"L2 transaction: {zks_tx_receipt['transactionHash'].hex()}")
    print(f"L1 transaction: {eth_tx_receipt['transactionHash'].hex()}")
    print(f"Effective ETH withdraw (paid fee): { Web3.from_wei(Web3.to_wei(amount, 'ether') - fee, 'ether')}")
