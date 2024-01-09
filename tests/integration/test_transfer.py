from unittest import main, TestCase, skip

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from web3 import Web3

from .test_config import LOCAL_ENV, EnvPrivateKey
from zksync2.core.types import EthBlockParams, ZkBlockParams
from zksync2.manage_contracts.zksync_contract import ZkSyncContract
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.provider.eth_provider import EthereumProvider
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxFunctionCall


class TransferTests(TestCase):
    def setUp(self) -> None:
        self.env = LOCAL_ENV
        self.zksync = ZkSyncBuilder.build(self.env.zksync_server)
        self.eth_web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        self.account1: LocalAccount = Account.from_key("7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110")
        self.account2: LocalAccount = Account.from_key("ac1e735be8536c6534bb4f17f06f6afc73b2b5ba84ac2cfb12f7461b20c0bbe3")
        self.signer = PrivateKeyEthSigner(self.account1, self.zksync.zksync.chain_id)
        self.eth_provider = EthereumProvider(self.zksync, self.eth_web3, self.account1)
        self.zksync_contract = ZkSyncContract(self.zksync.zksync.main_contract_address, self.eth_web3, self.account1)

    def test_transfer(self):
        amount = Web3.to_wei(1, "ether")
        account1_balance_before = self.zksync.zksync.get_balance(self.account1.address, EthBlockParams.LATEST.value)
        account2_balance_before = self.zksync.zksync.get_balance(self.account2.address, EthBlockParams.LATEST.value)

        nonce = self.zksync.zksync.get_transaction_count(
            self.account1.address, ZkBlockParams.COMMITTED.value
        )

        gas_price = self.zksync.zksync.gas_price

        tx_func_call = TxFunctionCall(
            chain_id=self.zksync.zksync.chain_id,
            nonce=nonce,
            from_=self.account1.address,
            to=self.account2.address,
            value=amount,
            data=HexStr("0x"),
            gas_limit=0,  # UNKNOWN AT THIS STATE
            gas_price=gas_price,
            max_priority_fee_per_gas=100000000,
        )

        estimate_gas = self.zksync.zksync.eth_estimate_gas(tx_func_call.tx)

        tx_712 = tx_func_call.tx712(estimate_gas)
        signed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(signed_message)
        tx_hash = self.zksync.zksync.send_raw_transaction(msg)

        tx_receipt = self.zksync.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )

        account1_balance_after = self.zksync.zksync.get_balance(self.account1.address, EthBlockParams.LATEST.value)
        account2_balance_after = self.zksync.zksync.get_balance(self.account2.address, EthBlockParams.LATEST.value)

        self.assertEqual(1, tx_receipt["status"], "Transaction should be successful")
        self.assertGreaterEqual(account2_balance_after, account2_balance_before + amount,
                                "Balance of account2 should be increased by amount")


if __name__ == '__main__':
    main()
