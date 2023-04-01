from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from zksync2.core.types import ZkBlockParams, ADDRESS_DEFAULT, Token
from zksync2.manage_contracts.erc20_contract import ERC20Contract, ERC20Encoder
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxFunctionCall

ZKSYNC_TEST_URL = "https://zksync2-testnet.zksync.dev"
ETH_TEST_URL = "https://rpc.ankr.com/eth_goerli"
PRIVATE_KEY = bytes.fromhex("fd1f96220fa3a40c46d65f81d61dd90af600746fd47e5c82673da937a48b38ef")
PRIVATE_KEY2 = bytes.fromhex("ba6852a8a14cd3c72f6cab8c08f70d033d5d1a56646ab04b4cf54c01cb7204dc")
SERC20_Address = Web3.to_checksum_address("0xd782e03F4818A7eDb0bc5f70748F67B4e59CdB33")


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


def transfer_erc20(amount: float):
    web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    alice: LocalAccount = Account.from_key(PRIVATE_KEY)
    bob: LocalAccount = Account.from_key(PRIVATE_KEY2)
    chain_id = web3.zksync.chain_id
    signer = PrivateKeyEthSigner(alice, chain_id)

    erc20_token = Token(l1_address=ADDRESS_DEFAULT,
                        l2_address=SERC20_Address,
                        symbol="SERC20",
                        decimals=18)
    erc20 = ERC20Contract(web3=web3.zksync,
                          contract_address=erc20_token.l2_address,
                          account=alice)

    alice_balance_before = erc20.balance_of(alice.address)
    bob_balance_before = erc20.balance_of(bob.address)
    print(f"Alice {erc20_token.symbol} balance before : {erc20_token.format_token(alice_balance_before)}")
    print(f"Bob {erc20_token.symbol} balance before : {erc20_token.format_token(bob_balance_before)}")

    erc20_encoder = ERC20Encoder(web3)
    transfer_params = (bob.address, erc20_token.to_int(amount))
    call_data = erc20_encoder.encode_method("transfer", args=transfer_params)

    nonce = web3.zksync.get_transaction_count(alice.address, ZkBlockParams.COMMITTED.value)

    gas_price = web3.zksync.gas_price
    func_call = TxFunctionCall(chain_id=chain_id,
                               nonce=nonce,
                               from_=alice.address,
                               to=erc20_token.l2_address,
                               data=call_data,
                               gas_limit=0,  # UNKNOWN AT THIS STATE
                               gas_price=gas_price,
                               max_priority_fee_per_gas=100000000)

    estimate_gas = web3.zksync.eth_estimate_gas(func_call.tx)
    print(f"Fee for transaction is: {estimate_gas * gas_price}")
    tx_712 = func_call.tx712(estimated_gas=estimate_gas)
    singed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    msg = tx_712.encode(singed_message)
    tx_hash = web3.zksync.send_raw_transaction(msg)
    tx_receipt = web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
    print(f"Tx status: {tx_receipt['status']}")
    print(f"Tx hash: {tx_receipt['transactionHash'].hex()}")

    alice_balance_after = erc20.balance_of(alice.address)
    bob_balance_after = erc20.balance_of(bob.address)
    print(f"Alice {erc20_token.symbol} balance before : {erc20_token.format_token(alice_balance_after)}")
    print(f"Bob {erc20_token.symbol} balance before : {erc20_token.format_token(bob_balance_after)}")

    if bob_balance_after == bob_balance_before + erc20_token.to_int(amount) and \
            alice_balance_after == alice_balance_before - erc20_token.to_int(amount):
        print(f"{Colors.OKGREEN}{amount} of {erc20_token.symbol} tokens have been transferred{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{erc20_token.symbol} transfer has failed{Colors.ENDC}")


if __name__ == "__main__":
    transfer_erc20(1)
