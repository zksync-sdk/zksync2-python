import os
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount

from examples.utils import EnvPrivateKey
from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.contract_factory import LegacyContractFactory
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner

ZKSYNC_TEST_URL = "http://127.0.0.1:3050"
ETH_TEST_URL = "http://127.0.0.1:8545"


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


def example(counter_contract: Path):
    env = EnvPrivateKey("ZKSYNC_TEST_KEY")
    web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    account: LocalAccount = Account.from_key(env.key())
    chain_id = web3.zksync.chain_id
    signer = PrivateKeyEthSigner(account, chain_id)

    increment_value = 10
    salt = generate_random_salt()
    deployer = LegacyContractFactory.from_json(zksync=web3,
                                               compiled_contract=counter_contract,
                                               account=account,
                                               signer=signer)
    contract = deployer.deploy(salt=salt)
    value = contract.functions.get().call({
        "from": account.address
    })
    print(f"Value before: {value}")

    gas_price = web3.zksync.gas_price
    nonce = web3.zksync.get_transaction_count(account.address, EthBlockParams.LATEST.value)
    tx = contract.functions.increment(increment_value).build_transaction({
        "nonce": nonce,
        "from": account.address,
        # INFO: this fields can't be got automatically because internally
        #      web3 py uses web3.eth provider with specific lambdas for getting them
        "maxPriorityFeePerGas": 1000000,
        "maxFeePerGas": gas_price
    })
    signed = account.sign_transaction(tx)
    tx_hash = web3.zksync.send_raw_transaction(signed.rawTransaction)
    tx_receipt = web3.zksync.wait_for_transaction_receipt(tx_hash)
    print(f"Tx Status: {tx_receipt['status']}")

    value = contract.functions.get().call(
        {
            "from": account.address,
        })
    print(f"Value after: {value}")
    if increment_value != value:
        print(f"{Colors.FAIL}unexpected value :{value}{Colors.ENDC}")
    else:
        print(f"{Colors.OKGREEN}Pass{Colors.ENDC}")


if __name__ == "__main__":
    contract_path = Path("../tests/contracts/Counter.json")
    example(contract_path)

