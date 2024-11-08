# Deposits token to l2 so that tests can run
# Creates paymaster and crown token
import json
import os
import sys
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from web3 import Web3


def main():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.join(current_directory, "..")
    sys.path.append(parent_directory)
    SALT = "0x293328ad84b118194c65a0dc0defdb6483740d3163fd99b260907e15f2e2f642"
    private_key_1 = HexStr(
        "0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110"
    )
    private_key_2 = HexStr(
        "0xac1e735be8536c6534bb4f17f06f6afc73b2b5ba84ac2cfb12f7461b20c0bbe3"
    )
    approval_token = HexStr("0x0183Fe07a98bc036d6eb23C3943d823bcD66a90F")
    dai_l1 = Web3.to_checksum_address("0x70a0F165d6f8054d0d0CF8dFd4DD2005f0AF6B55")

    from zksync2.account.wallet import Wallet
    from zksync2.manage_contracts.utils import get_zksync_hyperchain
    from zksync2.module.module_builder import ZkSyncBuilder
    from zksync2.signer.eth_signer import PrivateKeyEthSigner
    from zksync2.core.utils import LEGACY_ETH_ADDRESS
    from tests.integration.test_config import EnvURL

    env = EnvURL()
    zksync = ZkSyncBuilder.build(env.env.zksync_server)
    eth_web3 = Web3(Web3.HTTPProvider(env.env.eth_server))

    account: LocalAccount = Account.from_key(private_key_1)

    chain_id = zksync.zksync.chain_id
    signer = PrivateKeyEthSigner(account, chain_id)
    wallet = Wallet(zksync, eth_web3, account)
    zksync_contract = eth_web3.eth.contract(
        Web3.to_checksum_address(zksync.zksync.main_contract_address),
        abi=get_zksync_hyperchain(),
    )

    if not wallet.is_eth_based_chain():
        base_token = wallet.get_base_token()
        print("L1 base token balance before: ", wallet.get_l1_balance(token=base_token))
        print("L2 base token balance before: ", wallet.get_balance())
        deposit_token(wallet, base_token, eth_web3, zksync, zksync_contract)
        print("L1 base token balance after: ", wallet.get_l1_balance(token=base_token))
        print("L2 base token balance after: ", wallet.get_balance())

        print("L1 eth balance before: ", wallet.get_l1_balance())
        print(
            "L2 eth balance before: ",
            wallet.get_balance(token_address=LEGACY_ETH_ADDRESS),
        )
        deposit_token(wallet, LEGACY_ETH_ADDRESS, eth_web3, zksync, zksync_contract)
        print("L1 eth balance after: ", wallet.get_l1_balance())
        print(
            "L2 eth balance after: ",
            wallet.get_balance(token_address=LEGACY_ETH_ADDRESS),
        )

    dai_l2 = wallet.l2_token_address(address=dai_l1)
    print("L1 DAI token balance before: ", wallet.get_l1_balance(token=dai_l1))
    print("L2 DAI token balance before: ", wallet.get_balance(token_address=dai_l2))
    deposit_token(wallet, dai_l1, eth_web3, zksync, zksync_contract)
    print("L1 DAI token balance after: ", wallet.get_l1_balance(token=dai_l1))
    print("L2 DAI token balance after: ", wallet.get_balance(token_address=dai_l2))

    setup_paymaster(eth_web3, zksync, wallet, signer, SALT)
    deploy_multisig_contract(
        wallet, zksync, private_key_1, private_key_2, dai_l1, approval_token, SALT
    )


def deposit_token(wallet, token_address, eth_web3: Web3, zksync: Web3, zksync_contract):
    from zksync2.manage_contracts.utils import get_test_net_erc20_token
    from zksync2.core.types import EthBlockParams
    from zksync2.core.types import DepositTransaction

    token_contract = eth_web3.eth.contract(
        Web3.to_checksum_address(token_address), abi=get_test_net_erc20_token()
    )
    mint_tx = token_contract.functions.mint(
        wallet.address, Web3.to_wei(20000, "ether")
    ).build_transaction(
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
    tx_hash = eth_web3.eth.send_raw_transaction(signed.raw_transaction)
    eth_web3.eth.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)

    tx_hash = wallet.deposit(
        DepositTransaction(
            Web3.to_checksum_address(token_address),
            Web3.to_wei(10000, "ether"),
            wallet.address,
            approve_erc20=True,
            approve_base_erc20=True,
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

    mint_tx = token_contract.functions.mint(wallet.address, 1000).build_transaction(
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
    tx_hash = provider_l2.eth.send_raw_transaction(signed.raw_transaction)
    provider_l2.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )

    paymaster_address = deploy_paymaster(
        provider_l2, wallet, token_address, signer, salt
    )
    faucet_hash = wallet.transfer(
        TransferTransaction(to=paymaster_address, amount=provider_l2.to_wei(1, "ether"))
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

    print("Approval token contract address: ", tx_receipt["contractAddress"])

    return tx_receipt["contractAddress"]


def deploy_paymaster(provider_l2: Web3, wallet, token_address, signer, salt):
    from zksync2.core.types import EthBlockParams
    from zksync2.core.utils import to_bytes
    from zksync2.manage_contracts.contract_encoder_base import (
        JsonConfiguration,
        ContractEncoder,
    )
    from zksync2.transaction.transaction_builders import TxCreate2Contract
    from zksync2.manage_contracts.contract_factory import LegacyContractFactory
    from zksync2.manage_contracts.contract_factory import DeploymentType

    directory = Path(__file__).parent.parent
    path = directory / "tests/contracts/Paymaster.json"
    token_address = provider_l2.to_checksum_address(token_address)
    constructor_arguments = {"_erc20": token_address}

    deployer = LegacyContractFactory.from_json(
        zksync=provider_l2,
        compiled_contract=path.resolve(),
        account=signer,
        signer=signer,
        deployment_type=DeploymentType.CREATE2_ACCOUNT
    )
    contract = deployer.deploy(salt=to_bytes(salt), **constructor_arguments)

    # chain_id = provider_l2.zksync.chain_id
    # nonce = provider_l2.zksync.get_transaction_count(
    #     wallet.address, EthBlockParams.PENDING.value
    # )
    # token_contract = ContractEncoder.from_json(
    #     provider_l2, path.resolve(), JsonConfiguration.STANDARD
    # )
    # encoded_constructor = token_contract.encode_constructor(**constructor_arguments)
    # gas_price = provider_l2.zksync.gas_price
    # create_account = TxCreate2Contract(
    #     web3=provider_l2,
    #     chain_id=chain_id,
    #     gas_limit=0,
    #     nonce=nonce,
    #     from_=wallet.address,
    #     gas_price=gas_price,
    #     bytecode=token_contract.bytecode,
    #     call_data=encoded_constructor,
    #     salt=to_bytes(salt),
    # )
    # estimate_gas = provider_l2.zksync.eth_estimate_gas(create_account.tx)
    # tx_712 = create_account.tx712(estimate_gas)
    # signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    # msg = tx_712.encode(signed_message)
    # tx_hash = provider_l2.zksync.send_raw_transaction(msg)
    # tx_receipt = provider_l2.zksync.wait_for_transaction_receipt(
    #     tx_hash, timeout=240, poll_latency=0.5
    # )
    print("Paymaster contract address: ", contract.address)

    return contract.address


def deploy_multisig_contract(
    wallet, zksync, private_key_1, private_key_2, dai_l1, approval_token_l1, salt
):
    from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
    from zksync2.manage_contracts.contract_encoder_base import JsonConfiguration
    from zksync2.core.types import EthBlockParams
    from zksync2.transaction.transaction_builders import TxCreate2Account
    from zksync2.signer.eth_signer import PrivateKeyEthSigner
    from zksync2.core.types import TransferTransaction
    from zksync2.core.utils import LEGACY_ETH_ADDRESS
    from zksync2.core.utils import to_bytes

    directory = Path(__file__).parent.parent
    contract_path = directory / "tests/contracts/TwoUserMultisig.json"
    owner_1 = Account.from_key(private_key_1)
    owner_2 = Account.from_key(private_key_2)

    multisig_contract = ContractEncoder.from_json(
        zksync, contract_path, JsonConfiguration.STANDARD
    )
    constructor = multisig_contract.encode_constructor(
        **{"_owner1": owner_1.address, "_owner2": owner_2.address}
    )
    nonce = zksync.zksync.get_transaction_count(
        owner_1.address, EthBlockParams.PENDING.value
    )
    gas_price = zksync.zksync.gas_price

    create2_contract = TxCreate2Account(
        web3=zksync,
        chain_id=zksync.eth.chain_id,
        nonce=nonce,
        from_=owner_1.address,
        gas_limit=0,
        gas_price=gas_price,
        bytecode=multisig_contract.bytecode,
        call_data=constructor,
        salt=to_bytes(salt),
    )
    estimate_gas = zksync.zksync.eth_estimate_gas(create2_contract.tx)
    tx_712 = create2_contract.tx712(estimate_gas)
    signer = PrivateKeyEthSigner(owner_1, zksync.eth.chain_id)
    signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    msg = tx_712.encode(signed_message)
    tx_hash = zksync.zksync.send_raw_transaction(msg)
    deploy_tx = zksync.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )
    multisig_address = deploy_tx["contractAddress"]
    print("Multisig contract address: ", multisig_address)

    hash = wallet.transfer(
        TransferTransaction(to=multisig_address, amount=Web3.to_wei(100, "ether"))
    )
    zksync.zksync.wait_finalized(hash, timeout=240, poll_latency=0.5)

    hash = wallet.transfer(
        TransferTransaction(
            to=multisig_address, amount=100, token_address=approval_token_l1
        )
    )
    zksync.zksync.wait_finalized(hash, timeout=240, poll_latency=0.5)

    hash = wallet.transfer(
        TransferTransaction(
            to=multisig_address,
            amount=200,
            token_address=wallet.l2_token_address(dai_l1),
        )
    )
    zksync.zksync.wait_finalized(hash, timeout=240, poll_latency=0.5)

    if not wallet.is_eth_based_chain():
        wallet.transfer(
            TransferTransaction(
                to=multisig_address,
                amount=Web3.to_wei(100, "ether"),
                token_address=LEGACY_ETH_ADDRESS,
            )
        )


def load_token():
    directory = Path(__file__).parent.parent
    path = directory / "tests/integration/token.json"

    with open(path, "r") as file:
        data = json.load(file)
    return data[0]["address"]


if __name__ == "__main__":
    main()
