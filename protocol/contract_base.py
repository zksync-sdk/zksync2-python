from eth_account.signers.base import BaseAccount
from eth_typing import HexStr
from web3 import Web3


class ContractBase:

    def __init__(self, contract_address: HexStr, web3: Web3, account: BaseAccount, abi):
        self.contract_address = contract_address
        self.web3 = web3
        self.contract = self.web3.eth.contract(self.contract_address, abi=abi)  # type: ignore[call-overload]
        self.account = account

    def _call_method(self, method_name, *args, amount=None, **kwargs):
        params = {}
        if amount is not None:
            params['value'] = amount
        params['from'] = self.account.address
        transaction = getattr(self.contract.functions, method_name)(
            *args,
            **kwargs
        ).buildTransaction(params)

        transaction.update({'nonce': self.web3.eth.get_transaction_count(self.account.address)})
        signed_tx = self.account.sign_transaction(transaction)
        txn_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        txn_receipt = self.web3.eth.waitForTransactionReceipt(txn_hash)
        return txn_receipt
