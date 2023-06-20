import os

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexAddress, HexStr

from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.erc20_contract import get_erc20_abi
from zksync2.module.module_builder import ZkSyncBuilder


def transfer_erc20(
        token_contract,
        account: LocalAccount,
        address: HexAddress,
        amount: float) -> HexStr:
    """
       Transfer ETH to a desired address on zkSync network

       :param token_contract:
           Instance of ERC20 contract

       :param account:
           From which account the transfer will be made

       :param address:
         Desired ETH address that you want to transfer to.

       :param amount:
         Desired ETH amount that you want to transfer.

       :return:
         The transaction hash of the transfer transaction.

       """
    tx = token_contract.functions.transfer(address, amount).build_transaction({
        "nonce": zk_web3.zksync.get_transaction_count(account.address, EthBlockParams.LATEST.value),
        "from": account.address,
        "maxPriorityFeePerGas": 1_000_000,
        "maxFeePerGas": zk_web3.zksync.gas_price,
    })

    signed = account.sign_transaction(tx)

    # Send transaction to zkSync network
    tx_hash = zk_web3.zksync.send_raw_transaction(signed.rawTransaction)
    print(f"Tx: {tx_hash.hex()}")

    tx_receipt = zk_web3.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )
    print(f"Tx status: {tx_receipt['status']}")

    return tx_hash


if __name__ == "__main__":
    # Byte-format private key
    # PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))
    PRIVATE_KEY = bytes.fromhex("7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110")

    # Set a provider
    # PROVIDER = "https://testnet.era.zksync.dev"
    PROVIDER = "http://127.0.0.1:3050"

    # Connect to zkSync network
    zk_web3 = ZkSyncBuilder.build(PROVIDER)

    # Get account object by providing from private key
    account1: LocalAccount = Account.from_key(PRIVATE_KEY)
    account2_address = zk_web3.to_checksum_address("0xa61464658AfeAf65CccaaFD3a512b69A83B77618")

    token_address = zk_web3.to_checksum_address("0x2Ed5EfAB90d161DdCC65693bd77c3344200c9a00")
    token_contract = zk_web3.zksync.contract(token_address, abi=get_erc20_abi())

    # Show balance before token transfer
    print(f"Account1 Crown balance before transfer: {token_contract.functions.balanceOf(account1.address).call()}")
    print(f"Account2 Crown balance before transfer: {token_contract.functions.balanceOf(account2_address).call()}")

    # Perform the ETH transfer
    transfer_erc20(
        token_contract,
        account1,
        account2_address,
        3
    )

    # Show balance after token transfer
    print(f"Account1 Crown balance after transfer: {token_contract.functions.balanceOf(account1.address).call()}")
    print(f"Account2 Crown balance after transfer: {token_contract.functions.balanceOf(account2_address).call()}")
