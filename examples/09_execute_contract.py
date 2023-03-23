import os
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.types import TxParams, TxReceipt

from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxCreateContract, TxFunctionCall

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


class ContractExecutor:

    def __init__(self, compiled_contract: Path):
        self.compiled_contract = compiled_contract
        self.web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
        self.account: LocalAccount = Account.from_key(PRIVATE_KEY2)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.deployed_address = None
        self.contract_encoder = None

    def deploy(self):
        self.contract_encoder = ContractEncoder.from_json(self.web3, self.compiled_contract)
        random_salt = generate_random_salt()
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        gas_price = self.web3.zksync.gas_price
        create_contract = TxCreateContract(web3=self.web3,
                                           chain_id=self.chain_id,
                                           nonce=nonce,
                                           from_=self.account.address,
                                           gas_limit=0,  # UNKNOWN AT THIS STATE
                                           gas_price=gas_price,
                                           bytecode=self.contract_encoder.bytecode,
                                           salt=random_salt)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = create_contract.tx712(estimate_gas)
        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        print(f"Deploy status: {tx_receipt['status']}")
        contract_address = tx_receipt["contractAddress"]
        self.deployed_address = contract_address

    def execute_method(self, fn, args) -> TxReceipt:
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value)
        gas_price = self.web3.zksync.gas_price

        call_data = self.contract_encoder.encode_method(fn_name=fn, args=args)
        func_call = TxFunctionCall(chain_id=self.chain_id,
                                   nonce=nonce,
                                   from_=self.account.address,
                                   to=self.deployed_address,
                                   data=call_data,
                                   gas_limit=0,  # UNKNOWN AT THIS STATE,
                                   gas_price=gas_price)
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = func_call.tx712(estimate_gas)

        singed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        return tx_receipt

    def call_method(self, fn, args):
        encoded_get = self.contract_encoder.encode_method(fn_name=fn, args=args)
        eth_tx: TxParams = {
            "from": self.account.address,
            "to": self.deployed_address,
            "data": encoded_get,
        }
        eth_ret = self.web3.zksync.call(eth_tx, EthBlockParams.LATEST.value)
        return eth_ret


def example():
    contract = Path("../tests/contracts/Counter.json")
    executor = ContractExecutor(contract)
    executor.deploy()

    eth_ret = executor.call_method("get", [])
    val1 = int.from_bytes(eth_ret, "big", signed=True)
    print(f"Value before: {val1}")

    tx_receipt = executor.execute_method("increment", [1])
    if tx_receipt['status'] == 1:
        print(f"{Colors.OKGREEN}increment tx passed{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}increment failed{Colors.ENDC}")

    eth_ret = executor.call_method("get", [])
    val1 = int.from_bytes(eth_ret, "big", signed=True)
    print(f"Value after: {val1}")


if __name__ == "__main__":
    example()
