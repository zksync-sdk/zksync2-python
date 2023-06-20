import json
import os
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr

from zksync2.core.types import EthBlockParams, PaymasterParams
from zksync2.manage_contracts.paymaster_utils import PaymasterFlowEncoder
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxFunctionCall


def get_abi_from_standard_json(standard_json: Path):
    with standard_json.open(mode="r") as json_f:
        return json.load(json_f)["abi"]


"""
This example demonstrates how to use a paymaster to facilitate fee payment with an ERC20 token.
The user initiates a mint transaction that is configured to be paid with an ERC20 token through the paymaster.
During transaction execution, the paymaster receives the ERC20 token from the user and covers the transaction fee using ETH.
"""
if __name__ == "__main__":
    # Set a provider
    PROVIDER = "https://testnet.era.zksync.dev"

    # Byte-format private key
    PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))

    # Connect to zkSync network
    zk_web3 = ZkSyncBuilder.build(PROVIDER)

    # Get account object by providing from private key
    account: LocalAccount = Account.from_key(PRIVATE_KEY)

    # Crown token than can be minted for free
    token_address = zk_web3.to_checksum_address("0xCd9BDa1d0FC539043D4C80103bdF4f9cb108931B")
    # Paymaster for Crown token
    paymaster_address = zk_web3.to_checksum_address("0xd660c2F92d3d0634e5A20f26821C43F1b09298fe")

    # Provide a compiled JSON source contract
    token_path = Path("solidity/custom_paymaster/build/Token.json")

    token_contract = zk_web3.zksync.contract(token_address, abi=get_abi_from_standard_json(token_path))

    # MINT TOKEN TO USER ACCOUNT (so user can pay fee with token)
    balance = token_contract.functions.balanceOf(account.address).call()
    print(f"Crown token balance before mint: {balance}")

    mint_tx = token_contract.functions.mint(account.address, 15).build_transaction({
        "nonce": zk_web3.zksync.get_transaction_count(account.address, EthBlockParams.LATEST.value),
        "from": account.address,
        "maxPriorityFeePerGas": 1_000_000,
        "maxFeePerGas": zk_web3.zksync.gas_price,
    })

    signed = account.sign_transaction(mint_tx)

    # Send mint transaction to zkSync network
    tx_hash = zk_web3.zksync.send_raw_transaction(signed.rawTransaction)

    tx_receipt = zk_web3.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )
    print(f"Tx status: {tx_receipt['status']}")

    balance = token_contract.functions.balanceOf(account.address).call()
    print(f"Crown token balance after mint: {balance}")

    # SEND SOME ETH TO PAYMASTER (so it can pay fee with ETH)

    chain_id = zk_web3.zksync.chain_id
    gas_price = zk_web3.zksync.gas_price
    signer = PrivateKeyEthSigner(account, chain_id)

    tx_func_call = TxFunctionCall(
        chain_id=zk_web3.zksync.chain_id,
        nonce=zk_web3.zksync.get_transaction_count(account.address, EthBlockParams.LATEST.value),
        from_=account.address,
        to=paymaster_address,
        value=zk_web3.to_wei(1, "ether"),
        data=HexStr("0x"),
        gas_limit=0,  # Unknown at this state, estimation is done in next step
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

    # USE PAYMASTER TO PAY MINT TRANSACTION WITH CROWN TOKEN

    print(f"Paymaster balance before mint: "
          f"{zk_web3.zksync.get_balance(account.address, EthBlockParams.LATEST.value)}")
    print(f"User's Crown token balance before mint: {token_contract.functions.balanceOf(account.address).call()}")
    print(f"Paymaster balance before mint: "
          f"{zk_web3.zksync.get_balance(paymaster_address, EthBlockParams.LATEST.value)}")
    print(f"Paymaster Crown token balance before mint: {token_contract.functions.balanceOf(paymaster_address).call()}")

    # Use the paymaster to pay mint transaction with token
    calladata = token_contract.encodeABI(fn_name="mint", args=[account.address, 7])

    # Create paymaster parameters
    paymaster_params = PaymasterParams(**{
        "paymaster": paymaster_address,
        "paymaster_input": zk_web3.to_bytes(
            hexstr=PaymasterFlowEncoder(zk_web3).encode_approval_based(token_address, 1, b''))
    })

    tx_func_call = TxFunctionCall(
        chain_id=zk_web3.zksync.chain_id,
        nonce=zk_web3.zksync.get_transaction_count(account.address, EthBlockParams.LATEST.value),
        from_=account.address,
        to=token_address,
        data=calladata,
        gas_limit=0,  # Unknown at this state, estimation is done in next step
        gas_price=gas_price,
        max_priority_fee_per_gas=100_000_000,
        paymaster_params=paymaster_params
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

    print(f"Paymaster balance after mint: "
          f"{zk_web3.zksync.get_balance(account.address, EthBlockParams.LATEST.value)}")
    print(f"User's Crown token balance after mint: {token_contract.functions.balanceOf(account.address).call()}")
    print(f"Paymaster balance after mint: "
          f"{zk_web3.zksync.get_balance(paymaster_address, EthBlockParams.LATEST.value)}")
    print(f"Paymaster Crown token balance after mint: {token_contract.functions.balanceOf(paymaster_address).call()}")
