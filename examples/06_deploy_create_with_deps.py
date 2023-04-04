import os
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount

from examples.utils import EnvPrivateKey
from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.manage_contracts.nonce_holder import NonceHolder
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxCreateContract

ZKSYNC_TEST_URL = "http://127.0.0.1:3050"
ETH_TEST_URL = "http://127.0.0.1:8545"
PRIVATE_KEY2 = bytes.fromhex("fd1f96220fa3a40c46d65f81d61dd90af600746fd47e5c82673da937a48b38ef")


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def generate_random_salt() -> bytes:
    return os.urandom(32)


def deploy_create_with_deps(base_contract: Path,
                            dep_contract: Path):
    env = EnvPrivateKey("ZKSYNC_TEST_KEY")
    web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    account: LocalAccount = Account.from_key(env.key())
    chain_id = web3.zksync.chain_id
    signer = PrivateKeyEthSigner(account, chain_id)

    random_salt = generate_random_salt()
    import_contract = ContractEncoder.from_json(web3, base_contract)
    import_dependency_contract = ContractEncoder.from_json(web3, dep_contract)
    nonce = web3.zksync.get_transaction_count(account.address, EthBlockParams.PENDING.value)
    gas_price = web3.zksync.gas_price
    nonce_holder = NonceHolder(web3, account)
    deployment_nonce = nonce_holder.get_deployment_nonce(account.address)
    contract_deployer = PrecomputeContractDeployer(web3)
    precomputed_address = contract_deployer.compute_l2_create_address(account.address,
                                                                      deployment_nonce)

    create_contract = TxCreateContract(web3=web3,
                                       chain_id=chain_id,
                                       nonce=nonce,
                                       from_=account.address,
                                       gas_limit=0,
                                       gas_price=gas_price,
                                       bytecode=import_contract.bytecode,
                                       deps=[import_dependency_contract.bytecode],
                                       salt=random_salt)

    estimate_gas = web3.zksync.eth_estimate_gas(create_contract.tx)
    print(f"Fee for transaction is: {estimate_gas * gas_price}")

    tx_712 = create_contract.tx712(estimate_gas)

    singed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    msg = tx_712.encode(singed_message)
    tx_hash = web3.zksync.send_raw_transaction(msg)
    tx_receipt = web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
    print(f"Tx status: {tx_receipt['status']}")

    contract_address = contract_deployer.extract_contract_address(tx_receipt)
    print(f"contract address: {contract_address}")
    if precomputed_address.lower() == contract_address.lower():
        print(f"{Colors.OKGREEN}Precomputed address is eqaul to deployed: {contract_address}{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}Precomputed address does not equal to deployed{Colors.ENDC}")


if __name__ == "__main__":
    contract = Path("../tests/contracts/Import.json")
    dependent_contract = Path("../tests/contracts/Foo.json")
    deploy_create_with_deps(contract, dependent_contract)
