from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from web3 import Web3

from examples.utils import EnvPrivateKey
from zksync2.core.types import ZkBlockParams
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxFunctionCall

ZKSYNC_TEST_URL = "http://127.0.0.1:3050"
ETH_TEST_URL = "http://127.0.0.1:8545"


def transfer_native_to_self(amount: float):
    env = EnvPrivateKey("ZKSYNC_TEST_KEY")
    web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    account: LocalAccount = Account.from_key(env.key())
    chain_id = web3.zksync.chain_id
    signer = PrivateKeyEthSigner(account, chain_id)

    nonce = web3.zksync.get_transaction_count(account.address, ZkBlockParams.COMMITTED.value)
    gas_price = web3.zksync.gas_price
    tx_func_call = TxFunctionCall(chain_id=chain_id,
                                  nonce=nonce,
                                  from_=account.address,
                                  to=account.address,
                                  value=Web3.to_wei(amount, 'ether'),
                                  data=HexStr("0x"),
                                  gas_limit=0,  # UNKNOWN AT THIS STATE
                                  gas_price=gas_price,
                                  max_priority_fee_per_gas=100000000)
    estimate_gas = web3.zksync.eth_estimate_gas(tx_func_call.tx)
    print(f"Fee for transaction is: {estimate_gas * gas_price}")

    tx_712 = tx_func_call.tx712(estimate_gas)
    singed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    msg = tx_712.encode(singed_message)
    tx_hash = web3.zksync.send_raw_transaction(msg)
    tx_receipt = web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
    print(f"Tx status: {tx_receipt['status']}")


if __name__ == "__main__":
    transfer_native_to_self(0.1)
