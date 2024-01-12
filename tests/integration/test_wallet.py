from unittest import TestCase

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3

from tests.integration.test_config import LOCAL_ENV, EnvPrivateKey
from zksync2.account.wallet import Wallet
from zksync2.core.types import Token, EthBlockParams, DepositTransaction, ADDRESS_DEFAULT, FullDepositFee, \
    RequestExecuteCallMsg, RequestExecuteTransaction
from zksync2.manage_contracts.l2_bridge import L2Bridge
from zksync2.manage_contracts.zksync_contract import ZkSyncContract, _zksync_abi_default
from zksync2.module.module_builder import ZkSyncBuilder


class TestWallet(TestCase):
    def setUp(self) -> None:
        self.address = "0x36615Cf349d7F6344891B1e7CA7C72883F5dc049"
        self.env = LOCAL_ENV
        env_key = EnvPrivateKey("ZKSYNC_KEY1")
        self.zksync = ZkSyncBuilder.build(self.env.zksync_server)
        self.eth_web3 = Web3(Web3.HTTPProvider(self.env.eth_server))
        self.account: LocalAccount = Account.from_key(env_key.key)
        self.wallet = Wallet(self.zksync, self.eth_web3, self.account)
        self.zksync_contract = self.eth_web3.eth.contract(Web3.to_checksum_address(self.zksync.zksync.main_contract_address),
                                                abi=_zksync_abi_default())

    def test_get_main_contract(self):
        main_contract = self.wallet.main_contract
        self.assertIsNotNone(main_contract, "Should return main contract")

    def test_l1_bridge_contracts(self):
        contracts = self.wallet.get_l1_bridge_contracts()
        self.assertIsNotNone(contracts, "Should return l1 contracts")

    def test_get_l1_balance(self):
        balance = self.wallet.get_l1_balance()
        self.assertGreater(balance, 0, "Should return l1 balance")

    def test_get_allowance_l1(self):
        result = self.wallet.get_allowance_l1(HexStr("0xD13b85D93Ae5F7bb87CE65515F30F85Dd82A6281"))
        self.assertGreaterEqual(result, 0)

    def test_get_l2_token_address(self):
        address = self.wallet.l2_token_address(ADDRESS_DEFAULT)
        self.assertEqual(address, ADDRESS_DEFAULT, "Should return l2 token address")

    def test_approve_erc20(self):
        usdc_token = \
            Token(
                Web3.to_checksum_address("0xd35cceead182dcee0f148ebac9447da2c4d449c4"),
                Web3.to_checksum_address("0x852a4599217e76aa725f0ada8bf832a1f57a8a91"),
                "USDC",
                6)

        amount_usdc = 5
        is_approved = self.wallet.approve_erc20(usdc_token.l1_address, amount_usdc)
        self.assertIsNotNone(is_approved, "Should approve L1 token")

    def test_get_base_cost(self):
        base_cost = self.wallet.get_base_cost(l2_gas_limit=100_000)
        self.assertIsNotNone(base_cost, "Should return base cost")

    def test_get_balance(self):
        balance = self.wallet.get_balance()
        self.assertGreater(balance, 0, "Should return balance")

    def test_get_all_balances(self):
        balances = self.wallet.get_all_balances()
        self.assertEqual(len(balances), 1,"Should return all balances")

    def test_l2_bridge_contracts(self):
        contracts = self.wallet.get_l2_bridge_contracts()
        self.assertIsNotNone(contracts, "Should return l2 contracts")

    def test_get_address(self):
        address = self.wallet.address
        self.assertEqual(address, self.address, "Should return wallet address")

    def test_get_deployment_nonce(self):
        nonce = self.wallet.get_deployment_nonce()
        self.assertIsNotNone(nonce, "Should return deployment nonce")

    def test_prepare_deposit_transaction(self):
        tx = DepositTransaction(
            token=ADDRESS_DEFAULT,
            amount=7_000_000,
            to=self.wallet.address,
            operator_tip=0,
            l2_gas_limit=int("0x8d1c0", 16),
            gas_price=1_000_000_007,
            gas_per_pubdata_byte=800,
            max_fee_per_gas=1_000_000_010,
            refund_recipient=self.wallet.address,
            value=288_992_007_000_000,
            l2_value=7_000_000,
            max_priority_fee_per_gas=1_000_000_000
        )
        transaction = self.wallet.prepare_deposit_tx(tx)

        self.assertEqual(tx, transaction)

    def test_prepare_deposit_trabsaction_token(self):
        tx = DepositTransaction(
            token=HexStr("0x0F9765eda1627A1bB8e92653ed027D55eaa588ED"),
            amount=5,
            refund_recipient=self.wallet.address,
            to=self.wallet.get_l2_bridge_contracts().erc20.address,
            max_fee_per_gas=1_000_000_010,
            value=290_939_000_000_000,
            max_priority_fee_per_gas=1_000_000_000,
            custom_bridge_data=HexBytes("0xe8b99b1b00000000000000000000000036615cf349d7f6344891b1e7ca7c72883f5dc049000000000000000000000000881567b68502e6d7a7a3556ff4313b637ba47f4e0000000000000000000000000000000000000000000000000000000000000005000000000000000000000000000000000000000000000000000000000008e0f6000000000000000000000000000000000000000000000000000000000000032000000000000000000000000036615cf349d7f6344891b1e7ca7c72883f5dc049")
        )
        transaction = self.wallet.prepare_deposit_tx(tx)

        self.assertEqual(tx, transaction)

    def test_estimate_gas_deposit(self):
        estimated_gas = self.wallet.estimate_gas_deposit(DepositTransaction(
            token=ADDRESS_DEFAULT,
            to=self.wallet.address,
            amount=5,
            refund_recipient=self.wallet.address
        ))
        self.assertGreaterEqual(estimated_gas, 123_231)

    def test_deposit_eth(self):
        amount = Web3.to_wei(1, "ether")
        l2_balance_before = self.wallet.get_balance()

        l1_tx_receipt = self.wallet.deposit(DepositTransaction(token=Token.create_eth().l1_address,
                                            amount=amount,
                                            to=self.wallet.address))

        l2_hash = self.zksync.zksync.get_l2_hash_from_priority_op(l1_tx_receipt, self.zksync_contract)
        self.zksync.zksync.wait_for_transaction_receipt(l2_hash)
        l2_balance_after = self.wallet.get_balance()

        self.assertEqual(1, l1_tx_receipt["status"], "L1 transaction should be successful")
        self.assertGreaterEqual(l2_balance_after - l2_balance_before, amount, "Balance on L2 should be increased")

    # @skip("Integration test, used for develop purposes only")
    def test_deposit_token(self):
        amount_usdc = 5

        is_approved = self.wallet.approve_erc20(Web3.to_checksum_address("0x0F9765eda1627A1bB8e92653ed027D55eaa588ED"), amount_usdc)
        self.assertTrue(is_approved)
        balance_l1_before = self.wallet.get_l1_balance(Web3.to_checksum_address("0x0F9765eda1627A1bB8e92653ed027D55eaa588ED"))
        balance_l2_beore = self.wallet.get_balance(token_address=Web3.to_checksum_address("0xf2f2943B776F91a9e126FE3d2377363863437EC7"))
        tx_hash = self.wallet.deposit(DepositTransaction(Web3.to_checksum_address("0x0F9765eda1627A1bB8e92653ed027D55eaa588ED"),
                                                            amount_usdc,
                                                            self.account.address,
                                                            approve_erc20=True))

        l1_tx_receipt = self.eth_web3.eth.wait_for_transaction_receipt(tx_hash)

        zksync_contract = self.zksync_contract

        # Get hash of deposit transaction on L2 network
        l2_hash = self.zksync.zksync.get_l2_hash_from_priority_op(l1_tx_receipt, zksync_contract)

        # Wait for deposit transaction on L2 network to be finalized (5-7 minutes)
        self.zksync.zksync.wait_for_transaction_receipt(transaction_hash=l2_hash,
                                                                            timeout=360,
                                                                            poll_latency=10)

        balance_l2_after = self.wallet.get_balance(token_address=Web3.to_checksum_address("0xf2f2943B776F91a9e126FE3d2377363863437EC7"))
        balance_l1_after = self.wallet.get_l1_balance(Web3.to_checksum_address("0x0F9765eda1627A1bB8e92653ed027D55eaa588ED"))
        self.assertGreater(balance_l2_after, balance_l2_beore)
        self.assertGreater(balance_l1_before, balance_l1_after)

    def test_full_required_deposit_fee(self):
        fee_data=FullDepositFee(
            base_cost=286265000000000,
            l1_gas_limit=124231,
            l2_gas_limit=572530,
            max_fee_per_gas=1000000010,
            max_priority_fee_per_gas=1000000000)
        fee = self.wallet.get_full_required_deposit_fee(DepositTransaction(
            token=ADDRESS_DEFAULT,
            to=self.wallet.address
        ))
        self.assertEqual(fee, fee_data)

    def test_withdraw_eth(self):
        l2_balance_before = self.wallet.get_balance()
        amount = 0.005

        withdraw_tx_hash = self.wallet.withdraw(Token.create_eth().l1_address, Web3.to_wei(amount, "ether"))

        self.zksync.zksync.wait_for_transaction_receipt(
            withdraw_tx_hash, timeout=240, poll_latency=0.5
        )

        l2_balance_after = self.wallet.get_balance()

        self.assertGreater(l2_balance_before, l2_balance_after, "L2 balance should be lower after withdrawal")

    def test_withdraw_token(self):
        l2_balance_before = self.wallet.get_balance(token_address=Web3.to_checksum_address("0xf2f2943B776F91a9e126FE3d2377363863437EC7"))

        withdraw_tx_hash = self.wallet.withdraw(Web3.to_checksum_address("0xf2f2943B776F91a9e126FE3d2377363863437EC7"), 5)

        self.zksync.zksync.wait_for_transaction_receipt(
            withdraw_tx_hash, timeout=240, poll_latency=0.5
        )

        l2_balance_after = self.wallet.get_balance(token_address=Web3.to_checksum_address("0xf2f2943B776F91a9e126FE3d2377363863437EC7"))

        self.assertGreater(l2_balance_before, l2_balance_after, "L2 balance should be lower after withdrawal")

    def test_get_request_execute_transaction(self):
        result = self.wallet.get_request_execute_transaction(RequestExecuteCallMsg(
            contract_address=self.zksync_contract.address,
            call_data=HexStr("0x"),
            l2_value=7_000_000_000
        ))

        self.assertIsNotNone(result)

    def test_estimate_request_execute(self):
        result = self.wallet.estimate_gas_request_execute(RequestExecuteCallMsg(
            contract_address=self.zksync_contract.address,
            call_data=HexStr("0x"),
            l2_value=7_000_000_000
        ))

        self.assertGreater(result, 0)