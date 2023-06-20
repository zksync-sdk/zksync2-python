import os
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexAddress
from web3 import Web3

from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder, JsonConfiguration
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxCreate2Account


def generate_random_salt() -> bytes:
    return os.urandom(32)


def deploy_account(
        zk_web3: Web3, account: LocalAccount, compiled_contract: Path, constructor_args: [dict | tuple]
) -> HexAddress:
    """Deploy custom account on zkSync network using create2() opcode

    :param zk_web3:
        Instance of ZkSyncBuilder that interacts with zkSync network

    :param account:
        From which account the deployment contract tx will be made

    :param compiled_contract:
        Compiled custom account.

    :param constructor_args:
        Constructor arguments that can be provided via:
        dictionary: {"_erc20": token_address}
        tuple: tuple([token_address])

    :return:
        Address of deployed contract.

    """
    # Get chain id of zkSync network
    chain_id = zk_web3.zksync.chain_id

    # Signer is used to generate signature of provided transaction
    signer = PrivateKeyEthSigner(account, chain_id)

    # Get nonce of ETH address on zkSync network
    nonce = zk_web3.zksync.get_transaction_count(
        account.address, EthBlockParams.PENDING.value
    )

    # Deployment of same smart contract (same bytecode) without salt cannot be done twice
    # Remove salt if you want to deploy contract only once
    random_salt = generate_random_salt()

    # Precompute the address of smart contract
    # Use this if there is a case where contract address should be known before deployment
    deployer = PrecomputeContractDeployer(zk_web3)

    # Get contract ABI and bytecode information
    token_contract = ContractEncoder.from_json(zk_web3, compiled_contract, JsonConfiguration.STANDARD)

    # Encode the constructor arguments
    encoded_constructor = token_contract.encode_constructor(**constructor_args)

    # Get precomputed contract address
    precomputed_address = deployer.compute_l2_create2_address(sender=account.address,
                                                              bytecode=token_contract.bytecode,
                                                              constructor=encoded_constructor,
                                                              salt=random_salt)

    # Get current gas price in Wei
    gas_price = zk_web3.zksync.gas_price

    # Create2 account deployment transaction
    create2_account = TxCreate2Account(web3=zk_web3,
                                        chain_id=chain_id,
                                        nonce=nonce,
                                        from_=account.address,
                                        gas_limit=0,
                                        gas_price=gas_price,
                                        bytecode=token_contract.bytecode,
                                        salt=random_salt,
                                        call_data=encoded_constructor)

    # ZkSync transaction gas estimation
    estimate_gas = zk_web3.zksync.eth_estimate_gas(create2_account.tx)
    print(f"Fee for transaction is: {Web3.from_wei(estimate_gas * gas_price, 'ether')} ETH")

    # Convert transaction to EIP-712 format
    tx_712 = create2_account.tx712(estimate_gas)

    # Sign message
    signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())

    # Encode signed message
    msg = tx_712.encode(signed_message)

    # Deploy contract
    tx_hash = zk_web3.zksync.send_raw_transaction(msg)

    # Wait for deployment contract transaction to be included in a block
    tx_receipt = zk_web3.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )

    print(f"Tx status: {tx_receipt['status']}")
    contract_address = tx_receipt["contractAddress"]
    print(f"Account address: {contract_address}")

    # Check does precompute address match with deployed address
    if precomputed_address.lower() != contract_address.lower():
        raise RuntimeError("Precomputed contract address does now match with deployed contract address")

    return contract_address


if __name__ == "__main__":
    # Set a provider
    PROVIDER = "https://testnet.era.zksync.dev"

    # Byte-format private key
    PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))

    # Connect to zkSync network
    zk_web3 = ZkSyncBuilder.build(PROVIDER)

    # Get account object by providing from private key
    account: LocalAccount = Account.from_key(PRIVATE_KEY)

    # Provide a compiled JSON source contract
    contract_path = Path("solidity/custom_paymaster/build/Paymaster.json")

    # Crown token than can be minted for free
    token_address = zk_web3.to_checksum_address("0xCd9BDa1d0FC539043D4C80103bdF4f9cb108931B")
    constructor_arguments = {"_erc20": token_address}

    # Perform contract deployment
    deploy_account(zk_web3, account, contract_path, constructor_arguments)
