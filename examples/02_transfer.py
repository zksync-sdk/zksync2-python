import os

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr, HexAddress
from eth_utils import to_checksum_address
from web3 import Web3

from zksync2.core.types import ZkBlockParams, EthBlockParams
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxFunctionCall


def get_eth_balance(zk_web3: Web3, address: HexAddress) -> float:
    """
    Get ETH balance of ETH address on zkSync network

    :param zk_web3:
        Instance of ZkSyncBuilder that interacts with zkSync network

    :param address:
       ETH address that you want to get balance of.

    :return:
       Balance of ETH address.

    """

    # Get WEI balance of ETH address
    balance_wei = zk_web3.zksync.get_balance(
        address,
        EthBlockParams.LATEST.value
        )

    # Convert WEI balance to ETH
    balance_eth = Web3.from_wei(balance_wei, "ether")

    # Return the ETH balance of the ETH address
    return balance_eth


def transfer_eth(
    zk_web3: Web3,
    account: LocalAccount,
    address: HexAddress,
    amount: float
) -> bytes:
    """
    Transfer ETH to a desired address on zkSync network

    :param zk_web3:
        Instance of ZkSyncBuilder that interacts with zkSync network

    :param account:
        From which account the transfer will be made

    :param address:
      Desired ETH address that you want to transfer to.

    :param amount:
      Desired ETH amount that you want to transfer.

    :return:
      The transaction hash of the transfer transaction.

    """

    # Get chain id of zkSync network
    chain_id = zk_web3.zksync.chain_id

    # Signer is used to generate signature of provided transaction
    signer = PrivateKeyEthSigner(account, chain_id)

    # Get nonce of ETH address on zkSync network
    nonce = zk_web3.zksync.get_transaction_count(
        account.address, ZkBlockParams.COMMITTED.value
    )

    # Get current gas price in Wei
    gas_price = zk_web3.zksync.gas_price

    # Create transaction
    tx_func_call = TxFunctionCall(
        chain_id=chain_id,
        nonce=nonce,
        from_=account.address,
        to=to_checksum_address(address),
        value=zk_web3.to_wei(amount, "ether"),
        data=HexStr("0x"),
        gas_limit=0,  # UNKNOWN AT THIS STATE
        gas_price=gas_price,
        max_priority_fee_per_gas=100_000_000,
    )

    # ZkSync transaction gas estimation
    estimate_gas = zk_web3.zksync.eth_estimate_gas(tx_func_call.tx)
    print(f"Fee for transaction is: {estimate_gas * gas_price}")

    # Convert transaction to EIP-712 format
    tx_712 = tx_func_call.tx712(estimate_gas)

    # Sign message & encode it
    signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())

    # Encode signed message
    msg = tx_712.encode(signed_message)

    # Transfer ETH
    tx_hash = zk_web3.zksync.send_raw_transaction(msg)
    print(f"Transaction hash is : {tx_hash.hex()}")

    # Wait for transaction to be included in a block
    tx_receipt = zk_web3.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )
    print(f"Tx status: {tx_receipt['status']}")

    # Return the transaction hash of the transfer
    return tx_hash


if __name__ == "__main__":
    # Byte-format private key
    PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))

    # Set a provider
    PROVIDER = "https://testnet.era.zksync.dev"

    # Connect to zkSync network
    zk_web3 = ZkSyncBuilder.build(PROVIDER)

    # Get account object by providing from private key
    account: LocalAccount = Account.from_key(PRIVATE_KEY)

    # Show balance before ETH transfer
    print(f"Balance before transfer : {get_eth_balance(zk_web3, account.address)} ETH")

    # Perform the ETH transfer
    transfer_eth(
        zk_web3,
        account,
        to_checksum_address("0x81E9D85b65E9CC8618D85A1110e4b1DF63fA30d9"),
        0.001
        )

    # Show balance after ETH transfer
    print(f"Balance after transfer : {get_eth_balance(zk_web3, account.address)} ETH")
