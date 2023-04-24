import os
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.core.types import EthBlockParams
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxCreateContract

ZKSYNC_TEST_URL = "http://127.0.0.1:3050"







def deploy_contract(compiled_contract: Path):
    
    web3 = ZkSyncBuilder.build(ZKSYNC_TEST_URL)
    account: LocalAccount = Account.from_key(os.environ.get("PRIVATE_KEY"))
    chain_id = web3.zksync.chain_id
    signer = PrivateKeyEthSigner(account, chain_id)


    nonce = web3.zksync.get_transaction_count(account.address, EthBlockParams.PENDING.value)




    counter_contract = ContractEncoder.from_json(web3, compiled_contract)



    gas_price = web3.zksync.gas_price
    create_contract = TxCreateContract(web3=web3,
                                       chain_id=chain_id,
                                       nonce=nonce,
                                       from_=account.address,
                                       gas_limit=0,  # UNKNOWN AT THIS STATE
                                       gas_price=gas_price,
                                       bytecode=counter_contract.bytecode
                                       )
    estimate_gas = web3.zksync.eth_estimate_gas(create_contract.tx)
    print(f"Fee for transaction is: {estimate_gas * gas_price}")
    tx_712 = create_contract.tx712(estimate_gas)
    singed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    msg = tx_712.encode(singed_message)
    tx_hash = web3.zksync.send_raw_transaction(msg)
    tx_receipt = web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)

    print(f"Tx status: {tx_receipt['status']}")
    contract_address = tx_receipt["contractAddress"]

    print(f"Deployed contract address: {contract_address}")




if __name__ == "__main__":
    contract_path = Path("")
    deploy_contract(contract_path)
