from unittest import main, TestCase

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.middleware import geth_poa_middleware

from test_config import LOCAL_ENV, EnvPrivateKey
from zksync2.core.types import Token, EthBlockParams
from zksync2.manage_contracts.zksync_contract import ZkSyncContract
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.provider.eth_provider import EthereumProvider
from zksync2.transaction.transaction_builders import TxWithdraw


class WithdrawTests(TestCase):
    def setUp(self) -> None:
        self.env = LOCAL_ENV
        env_key = EnvPrivateKey("ZKSYNC_KEY1")
        self.zksync = ZkSyncBuilder.build(self.env.zksync_server)
        self.eth_web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        self.eth_web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.account: LocalAccount = Account.from_key(env_key.key)
        self.eth_provider = EthereumProvider(self.zksync, self.eth_web3, self.account)
        self.zksync_contract = ZkSyncContract(self.zksync.zksync.main_contract_address,
                                              self.eth_web3, self.account)

    def test_withdraw(self):
        amount = Web3.to_wei(1, "ether")
        eth_token = Token.create_eth()
        l1_balance_before = self.eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
        l2_balance_before = self.zksync.zksync.get_balance(self.account.address, EthBlockParams.LATEST.value)

        print(f"L1 balance before withdraw: {Web3.from_wei(l1_balance_before, 'ether')} ETH")
        print(f"L2 balance before withdraw: {Web3.from_wei(l2_balance_before, 'ether')} ETH")

        withdraw = TxWithdraw(web3=self.zksync,
                              token=Token.create_eth(),
                              amount=amount,
                              gas_limit=0,  # unknown
                              account=self.account)
        estimated_gas = self.zksync.zksync.eth_estimate_gas(withdraw.tx)
        tx = withdraw.estimated_gas(estimated_gas)
        signed = self.account.sign_transaction(tx)
        tx_hash = self.zksync.zksync.send_raw_transaction(signed.rawTransaction)
        l2_tx_receipt = self.zksync.zksync.wait_finalized(tx_hash, timeout=240, poll_latency=0.5)

        self.assertEqual(1, l2_tx_receipt["status"], "L2 transaction should be successful")

        l1_tx_receipt = self.eth_provider.finalize_withdrawal(l2_tx_receipt["transactionHash"])
        self.assertEqual(1, l1_tx_receipt["status"])

        l1_balance_after = self.eth_provider.get_l1_balance(eth_token, EthBlockParams.LATEST)
        l2_balance_after = self.zksync.zksync.get_balance(self.account.address, EthBlockParams.LATEST.value)
        fee = l1_tx_receipt["gasUsed"] * l1_tx_receipt["effectiveGasPrice"]
        withdraw_absolute = amount - fee
        diff = l1_balance_after - l1_balance_before

        print(f"L1 transaction: {l1_tx_receipt['transactionHash'].hex()}")
        print(f"L2 transaction: {l2_tx_receipt['transactionHash'].hex()}")
        print(f"L1 balance after withdraw: {Web3.from_wei(l1_balance_after, 'ether')} ETH")
        print(f"L2 balance after withdraw: {Web3.from_wei(l2_balance_after, 'ether')} ETH")
        print(f"Effective ETH withdrew (paid fee): {Web3.from_wei(diff, 'ether')}")

        self.assertEqual(withdraw_absolute, diff, "Withdraw amount should be: amount - fee")
        self.assertEqual(1, l1_tx_receipt["status"], "L1 transaction should be successful")


if __name__ == '__main__':
    main()
