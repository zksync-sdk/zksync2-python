# Deposits token to l2 so that tests can run
# Creates paymaster and crown token
import json
import os
import sys
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3


def main():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.join(current_directory, "..")
    sys.path.append(parent_directory)
    SALT = "0x293328ad84b118194c65a0dc0defdb6483740d3163fd99b260907e15f2e2f642"

    from zksync2.account.wallet import Wallet
    from zksync2.manage_contracts.utils import zksync_abi_default
    from zksync2.module.module_builder import ZkSyncBuilder
    from zksync2.signer.eth_signer import PrivateKeyEthSigner

    zksync = ZkSyncBuilder.build("http://127.0.0.1:3050")
    eth_web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    account: LocalAccount = Account.from_key(
        "0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110"
    )

    chain_id = zksync.zksync.chain_id
    signer = PrivateKeyEthSigner(account, chain_id)
    wallet = Wallet(zksync, eth_web3, account)
    zksync_contract = eth_web3.eth.contract(
        Web3.to_checksum_address(zksync.zksync.main_contract_address),
        abi=zksync_abi_default(),
    )

    deposit_token(wallet, eth_web3, zksync, zksync_contract)
    setup_paymaster(eth_web3, zksync, wallet, signer, SALT)


def deposit_token(wallet, eth_web3: Web3, zksync: Web3, zksync_contract):
    from zksync2.core.types import DepositTransaction
    from zksync2.manage_contracts.utils import get_test_net_erc20_token
    from zksync2.core.types import EthBlockParams

    amount = 100
    l1_address = load_token()

    token_contract = eth_web3.eth.contract(
        Web3.to_checksum_address(l1_address), abi=get_test_net_erc20_token()
    )
    mint_tx = token_contract.functions.mint(wallet.address, 10000).build_transaction(
        {
            "nonce": eth_web3.eth.get_transaction_count(
                wallet.address, EthBlockParams.LATEST.value
            ),
            "from": wallet.address,
            "maxPriorityFeePerGas": 1_000_000,
            "maxFeePerGas": eth_web3.eth.gas_price,
        }
    )

    signed = wallet.sign_transaction(mint_tx)
    tx_hash = eth_web3.eth.send_raw_transaction(signed.rawTransaction)
    eth_web3.eth.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)

    tx_hash = wallet.deposit(
        DepositTransaction(
            Web3.to_checksum_address(l1_address),
            amount,
            wallet.address,
            approve_erc20=True,
            refund_recipient=wallet.address,
        )
    )

    l1_tx_receipt = eth_web3.eth.wait_for_transaction_receipt(tx_hash)

    l2_hash = zksync.zksync.get_l2_hash_from_priority_op(l1_tx_receipt, zksync_contract)
    zksync.zksync.wait_for_transaction_receipt(
        transaction_hash=l2_hash, timeout=360, poll_latency=10
    )


def setup_paymaster(provider_l1, provider_l2, wallet, signer, salt):
    from zksync2.core.types import EthBlockParams, TransferTransaction
    from zksync2.manage_contracts.contract_encoder_base import (
        JsonConfiguration,
        ContractEncoder,
    )
    from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses

    directory = Path(__file__).parent.parent
    path = directory / "tests/contracts/Token.json"

    token_contract = ContractEncoder.from_json(
        provider_l2, path.resolve(), JsonConfiguration.STANDARD
    )
    abi = token_contract.abi

    token_address = deploy_crown_token(
        provider_l2, wallet, signer, salt, token_contract
    )
    token_contract = provider_l2.zksync.contract(token_address, abi=abi)

    mint_tx = token_contract.functions.mint(wallet.address, 15).build_transaction(
        {
            "nonce": provider_l2.zksync.get_transaction_count(
                wallet.address, EthBlockParams.LATEST.value
            ),
            "from": wallet.address,
            "maxPriorityFeePerGas": 1_000_000,
            "maxFeePerGas": provider_l2.zksync.gas_price,
        }
    )

    signed = wallet.sign_transaction(mint_tx)
    tx_hash = provider_l2.eth.send_raw_transaction(signed.rawTransaction)
    provider_l2.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )

    paymaster_address = deploy_paymaster(
        provider_l2, wallet, token_address, signer, salt
    )
    faucet_hash = wallet.transfer(
        TransferTransaction(
            to=paymaster_address,
            amount=provider_l2.to_wei(1, "ether"),
            token_address=ZkSyncAddresses.ETH_ADDRESS.value,
        )
    )

    provider_l2.zksync.wait_for_transaction_receipt(
        faucet_hash, timeout=240, poll_latency=0.5
    )


def deploy_crown_token(provider_l2, wallet, signer, salt, token_contract):
    from zksync2.core.types import EthBlockParams
    from zksync2.core.utils import to_bytes
    from zksync2.transaction.transaction_builders import TxCreate2Contract

    constructor_arguments = {"name_": "Ducat", "symbol_": "Ducat", "decimals_": 18}
    chain_id = provider_l2.zksync.chain_id
    nonce = provider_l2.zksync.get_transaction_count(
        wallet.address, EthBlockParams.PENDING.value
    )
    encoded_constructor = token_contract.encode_constructor(**constructor_arguments)

    gas_price = provider_l2.zksync.gas_price
    create2_contract = TxCreate2Contract(
        web3=provider_l2,
        chain_id=chain_id,
        nonce=nonce,
        from_=wallet.address,
        gas_limit=0,
        gas_price=gas_price,
        bytecode=token_contract.bytecode,
        salt=to_bytes(salt),
        call_data=encoded_constructor,
    )
    estimate_gas = provider_l2.zksync.eth_estimate_gas(create2_contract.tx)
    tx_712 = create2_contract.tx712(estimate_gas)
    signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    msg = tx_712.encode(signed_message)
    tx_hash = provider_l2.zksync.send_raw_transaction(msg)
    tx_receipt = provider_l2.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )

    return tx_receipt["contractAddress"]


def deploy_paymaster(provider_l2: Web3, wallet, token_address, signer, salt):
    from zksync2.core.types import EthBlockParams
    from zksync2.core.utils import to_bytes
    from zksync2.manage_contracts.contract_encoder_base import (
        JsonConfiguration,
        ContractEncoder,
    )
    from zksync2.transaction.transaction_builders import TxCreate2Contract

    directory = Path(__file__).parent.parent
    path = directory / "tests/contracts/Paymaster.json"
    token_address = provider_l2.to_checksum_address(token_address)
    constructor_arguments = {"_erc20": token_address}

    chain_id = provider_l2.zksync.chain_id
    nonce = provider_l2.zksync.get_transaction_count(
        wallet.address, EthBlockParams.PENDING.value
    )
    token_contract = ContractEncoder.from_json(
        provider_l2, path.resolve(), JsonConfiguration.STANDARD
    )
    encoded_constructor = token_contract.encode_constructor(**constructor_arguments)
    gas_price = provider_l2.zksync.gas_price
    create_account = TxCreate2Contract(
        web3=provider_l2,
        chain_id=chain_id,
        gas_limit=0,
        nonce=nonce,
        from_=wallet.address,
        gas_price=gas_price,
        bytecode=token_contract.bytecode,
        call_data=encoded_constructor,
        salt=to_bytes(salt),
    )
    estimate_gas = provider_l2.zksync.eth_estimate_gas(create_account.tx)
    tx_712 = create_account.tx712(estimate_gas)
    signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    msg = tx_712.encode(signed_message)
    tx_hash = provider_l2.zksync.send_raw_transaction(msg)
    tx_receipt = provider_l2.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )
    return tx_receipt["contractAddress"]


def load_token():
    directory = Path(__file__).parent.parent
    path = directory / "tests/integration/token.json"

    with open(path, "r") as file:
        data = json.load(file)
    return data[0]["address"]


if __name__ == "__main__":
    main()
