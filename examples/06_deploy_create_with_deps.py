import os
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.manage_contracts.nonce_holder import NonceHolder
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxCreateContract


def generate_random_salt() -> bytes:
    return os.urandom(32)


def deploy_contract(
        zk_web3: Web3, account: LocalAccount, compiled_contract: Path
):
    """Deploy compiled contract with dependency on zkSync network using create() opcode

    :param zk_web3:
        Instance of ZkSyncBuilder that interacts with zkSync network

    :param account:
        From which account the deployment contract tx will be made

    :param compiled_contract:
        Compiled contract source.

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

    # Get deployment nonce
    nonce_holder = NonceHolder(zk_web3, account)
    deployment_nonce = nonce_holder.get_deployment_nonce(account.address)

    # Precompute the address of smart contract
    # Use this if there is a case where contract address should be known before deployment
    deployer = PrecomputeContractDeployer(zk_web3)
    precomputed_address = deployer.compute_l2_create_address(account.address, deployment_nonce)

    # Get ABI and bytecode of demo and foo contracts
    demo_contract, foo_contract = ContractEncoder.from_json(zk_web3, compiled_contract)

    # Get current gas price in Wei
    gas_price = zk_web3.zksync.gas_price

    # Create deployment contract transaction
    create_contract = TxCreateContract(web3=zk_web3,
                                       chain_id=chain_id,
                                       nonce=nonce,
                                       from_=account.address,
                                       gas_price=gas_price,
                                       bytecode=demo_contract.bytecode,
                                       deps=[foo_contract.bytecode])

    # ZkSync transaction gas estimation
    estimate_gas = zk_web3.zksync.eth_estimate_gas(create_contract.tx)
    print(f"Fee for transaction is: {Web3.from_wei(estimate_gas * gas_price, 'ether')} ETH")

    # Convert transaction to EIP-712 format
    tx_712 = create_contract.tx712(estimate_gas)

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
    print(f"Contract address: {contract_address}")

    # Check does precompute address match with deployed address
    if precomputed_address.lower() != contract_address.lower():
        raise RuntimeError("Precomputed contract address does now match with deployed contract address")


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
    contract_path = Path("solidity/demo/build/combined.json")

    # Perform contract deployment
    deploy_contract(zk_web3, account, contract_path)
