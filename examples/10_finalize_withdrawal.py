import os

from eth_account import Account
from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import TxReceipt

from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.provider.eth_provider import EthereumProvider


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

    # Get the withdrawal transaction hash from OS environment variables
    WITHDRAW_TX_HASH = HexBytes.fromhex(os.environ.get("WITHDRAW_TX_HASH"))

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

    # Finalize withdraw of previous successful withdraw transaction
    eth_tx_receipt = finalize_withdraw(zk_web3, eth_provider, WITHDRAW_TX_HASH)

    fee = eth_tx_receipt["gasUsed"] * eth_tx_receipt["effectiveGasPrice"]
    amount = 0.01
    print(f"Finalize withdraw transaction: {eth_tx_receipt['transactionHash'].hex()}")
    print(f"Effective ETH withdraw (paid fee): {Web3.from_wei(Web3.to_wei(amount, 'ether') - fee, 'ether')}")
