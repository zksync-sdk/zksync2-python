import json
import os
from pathlib import Path
from time import sleep
from unittest import TestCase, skip

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3

from tests.integration.test_config import LOCAL_ENV, EnvPrivateKey
from zksync2.account.wallet import Wallet
from zksync2.core.types import (
    Token,
    DepositTransaction,
    ADDRESS_DEFAULT,
    FullDepositFee,
    RequestExecuteCallMsg,
    TransactionOptions,
    TransferTransaction,
    WithdrawTransaction,
    EthBlockParams, PaymasterParams, ZkBlockParams,
)
from zksync2.manage_contracts.contract_encoder_base import (
    ContractEncoder,
    JsonConfiguration,
)
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.paymaster_utils import PaymasterFlowEncoder
from zksync2.manage_contracts.precompute_contract_deployer import (
    PrecomputeContractDeployer,
)
from zksync2.manage_contracts.utils import zksync_abi_default, get_erc20_abi
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxCreate2Contract, TxCreateContract, TxFunctionCall


class TestWallet(TestCase):
    def setUp(self) -> None:
        self.token_address = "0x0183Fe07a98bc036d6eb23C3943d823bcD66a90F"
        self.paymaster_address = "0x594E77D36eB367b3AbAb98775c99eB383079F966"
        self.address2 = "0xa61464658AfeAf65CccaaFD3a512b69A83B77618"
        self.env = LOCAL_ENV
        env_key = EnvPrivateKey("ZKSYNC_KEY1")
        self.zksync = ZkSyncBuilder.build("http://127.0.0.1:3050")
        self.eth_web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
        self.account: LocalAccount = Account.from_key(env_key.key)
        self.wallet = Wallet(self.zksync, self.eth_web3, self.account)
        self.zksync_contract = self.eth_web3.eth.contract(
            Web3.to_checksum_address(self.zksync.zksync.main_contract_address),
            abi=zksync_abi_default(),
        )

    def load_token(self):
        directory = Path(__file__).parent
        path = directory / Path("token.json")

        with open(path, "r") as file:
            data = json.load(file)
        l1_address = data[0]["address"]
        l2_address = self.zksync.zksync.l2_token_address(l1_address)
        return l1_address, l2_address

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
        l1_address, l2_address = self.load_token()
        result = self.wallet.get_allowance_l1(HexStr(l1_address))
        self.assertGreaterEqual(result, 0)

    def test_get_l2_token_address(self):
        address = self.wallet.l2_token_address(ADDRESS_DEFAULT)
        self.assertEqual(address, ADDRESS_DEFAULT, "Should return l2 token address")

    def test_approve_erc20(self):
        usdc_token = Token(
            Web3.to_checksum_address("0xd35cceead182dcee0f148ebac9447da2c4d449c4"),
            Web3.to_checksum_address("0x852a4599217e76aa725f0ada8bf832a1f57a8a91"),
            "USDC",
            6,
        )

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
        self.assertGreaterEqual(len(balances), 1, "Should return all balances")

    def test_l2_bridge_contracts(self):
        contracts = self.wallet.get_l2_bridge_contracts()
        self.assertIsNotNone(contracts, "Should return l2 contracts")

    def test_get_address(self):
        address = self.wallet.address
        self.assertEqual(
            address,
            "0x36615Cf349d7F6344891B1e7CA7C72883F5dc049",
            "Should return wallet address",
        )

    def test_get_deployment_nonce(self):
        nonce = self.wallet.get_deployment_nonce()
        self.assertIsNotNone(nonce, "Should return deployment nonce")

    def test_prepare_deposit_transaction(self):
        options = TransactionOptions(
            gas_price=1_000_000_007,
            max_fee_per_gas=1_000_000_010,
            value=288_992_007_000_000,
            max_priority_fee_per_gas=1_000_000_000,
        )
        tx = DepositTransaction(
            token=ADDRESS_DEFAULT,
            amount=0.000000007,
            to=self.wallet.address,
            operator_tip=0,
            l2_gas_limit=int("0x8d1c0", 16),
            gas_per_pubdata_byte=800,
            refund_recipient=self.wallet.address,
            l2_value=7_000_000,
            options=options,
        )
        transaction = self.wallet.prepare_deposit_tx(tx)

        self.assertEqual(tx, transaction)

    def test_prepare_deposit_transaction_token(self):
        l1_address, l2_address = self.load_token()
        tx = DepositTransaction(
            token=HexStr(l1_address),
            amount=5,
            refund_recipient=self.wallet.address,
            to=self.wallet.get_l2_bridge_contracts().erc20.address,
            custom_bridge_data=HexBytes(
                "0xe8b99b1b00000000000000000000000036615cf349d7f6344891b1e7ca7c72883f5dc049000000000000000000000000881567b68502e6d7a7a3556ff4313b637ba47f4e0000000000000000000000000000000000000000000000000000000000000005000000000000000000000000000000000000000000000000000000000008e0f6000000000000000000000000000000000000000000000000000000000000032000000000000000000000000036615cf349d7f6344891b1e7ca7c72883f5dc049"
            ),
        )
        transaction = self.wallet.prepare_deposit_tx(tx)

        self.assertEqual(tx, transaction)

    def test_estimate_gas_deposit(self):
        estimated_gas = self.wallet.estimate_gas_deposit(
            DepositTransaction(
                token=ADDRESS_DEFAULT,
                to=self.wallet.address,
                amount=5,
                refund_recipient=self.wallet.address,
            )
        )
        self.assertGreaterEqual(estimated_gas, 110_581)

    def test_deposit_eth(self):
        amount = 7_000_000_000
        l2_balance_before = self.wallet.get_balance()

        tx_hash = self.wallet.deposit(
            DepositTransaction(token=Token.create_eth().l1_address, amount=amount)
        )

        tx_receipt = self.eth_web3.eth.wait_for_transaction_receipt(tx_hash)
        l2_hash = self.zksync.zksync.get_l2_hash_from_priority_op(
            tx_receipt, self.zksync_contract
        )
        self.zksync.zksync.wait_for_transaction_receipt(
            transaction_hash=l2_hash, timeout=360, poll_latency=10
        )
        l2_balance_after = self.wallet.get_balance()
        self.assertEqual(1, tx_receipt["status"], "L1 transaction should be successful")
        self.assertGreaterEqual(
            l2_balance_after - l2_balance_before,
            amount,
            "Balance on L2 should be increased",
        )

    # @skip("Integration test, used for develop purposes only")
    def test_deposit_token(self):
        amount = 100
        l1_address, l2_address = self.load_token()
        is_approved = self.wallet.approve_erc20(
            Web3.to_checksum_address(l1_address), amount
        )
        self.assertTrue(is_approved)

        balance_l2_beore = self.wallet.get_balance(
            token_address=Web3.to_checksum_address(l2_address)
        )

        tx_hash = self.wallet.deposit(
            DepositTransaction(
                Web3.to_checksum_address(l1_address),
                amount,
                self.account.address,
                approve_erc20=True,
                refund_recipient=self.wallet.address,
            )
        )

        l1_tx_receipt = self.eth_web3.eth.wait_for_transaction_receipt(tx_hash)

        l2_hash = self.zksync.zksync.get_l2_hash_from_priority_op(
            l1_tx_receipt, self.zksync_contract
        )
        self.zksync.zksync.wait_for_transaction_receipt(
            transaction_hash=l2_hash, timeout=360, poll_latency=10
        )

        balance_l2_after = self.wallet.get_balance(
            token_address=Web3.to_checksum_address(l2_address)
        )
        self.assertGreater(balance_l2_after, balance_l2_beore)

    def test_full_required_deposit_fee(self):
        fee_data = FullDepositFee(
            base_cost=285096500000000,
            l1_gas_limit=110581,
            l2_gas_limit=570193,
            max_fee_per_gas=1500000010,
            max_priority_fee_per_gas=1500000000,
        )
        fee = self.wallet.get_full_required_deposit_fee(
            DepositTransaction(token=ADDRESS_DEFAULT, to=self.wallet.address)
        )
        self.assertEqual(fee, fee_data)

    def test_transfer_eth(self):
        amount = 7_000_000_000
        balance_before_transfer = self.zksync.zksync.get_balance(
            Web3.to_checksum_address(self.address2)
        )
        tx_hash = self.wallet.transfer(
            TransferTransaction(
                to=Web3.to_checksum_address(self.address2),
                token_address=ADDRESS_DEFAULT,
                amount=amount
            )
        )

        self.zksync.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        balance_after_transfer = self.zksync.zksync.get_balance(
            Web3.to_checksum_address(self.address2)
        )

        self.assertEqual(balance_after_transfer - balance_before_transfer, amount)

    def test_transfer_eth_paymaster(self):
        amount = 1
        paymaster_address = self.zksync.to_checksum_address(self.paymaster_address)
        token_address = self.zksync.to_checksum_address(self.token_address)

        paymaster_balance_before = self.zksync.zksync.zks_get_balance(paymaster_address)
        paymaster_token_balance_before = self.zksync.zksync.zks_get_balance(paymaster_address, token_address=token_address)

        sender_balance_before = self.wallet.get_balance()
        sender_approval_token_balance_before = self.wallet.get_balance(token_address=token_address)
        reciever_balance_before = self.zksync.zksync.zks_get_balance(self.address2)

        paymaster_params = PaymasterParams(
            **{
                "paymaster": paymaster_address,
                "paymaster_input": self.eth_web3.to_bytes(
                    hexstr=PaymasterFlowEncoder(self.eth_web3).encode_approval_based(
                        token_address, 1, b""
                    )
                ),
            }
        )

        tx_hash = self.wallet.transfer(
            TransferTransaction(
                to=Web3.to_checksum_address(self.address2),
                token_address=ADDRESS_DEFAULT,
                amount=amount,
                paymaster_params=paymaster_params
            )
        )

        self.zksync.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )

        paymaster_balance_after = self.zksync.zksync.zks_get_balance(paymaster_address)
        paymaster_token_balance_after = self.zksync.zksync.zks_get_balance(paymaster_address, token_address=token_address)
        sender_balance_after = self.wallet.get_balance()
        sender_approval_token_balance_after = self.wallet.get_balance(token_address=token_address)
        reciever_balance_after = self.zksync.zksync.zks_get_balance(self.address2)

        self.assertGreaterEqual(paymaster_balance_before - paymaster_balance_after, 0)
        self.assertGreaterEqual(paymaster_token_balance_after - paymaster_token_balance_before, 0)
        self.assertGreaterEqual(sender_balance_before - sender_balance_after, 0)
        self.assertGreater(sender_approval_token_balance_before - sender_approval_token_balance_after, 0)
        self.assertGreaterEqual(reciever_balance_after - reciever_balance_before, 0)

    @skip("Used only for development purpose to refill paymaster")
    def test_mint_paymaster(self):
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Token.json")

        token_contract = ContractEncoder.from_json(
            self.zksync, path.resolve(), JsonConfiguration.STANDARD
        )
        abi = token_contract.abi
        token_contract = self.zksync.zksync.contract(Web3.to_checksum_address(self.token_address), abi=abi)

        balance_before = self.wallet.get_balance(Web3.to_checksum_address(self.token_address))
        mint_tx = token_contract.functions.mint(
            self.wallet.address, 15
        ).build_transaction(
            {
                "nonce": self.zksync.zksync.get_transaction_count(
                    self.wallet.address, EthBlockParams.LATEST.value
                ),
                "from": self.wallet.address,
                "maxPriorityFeePerGas": 1_000_000,
                "maxFeePerGas": self.zksync.zksync.gas_price,
            }
        )

        signed = self.wallet.sign_transaction(mint_tx)
        tx_hash = self.zksync.eth.send_raw_transaction(signed.rawTransaction)
        self.zksync.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        balance_after = self.wallet.get_balance(Web3.to_checksum_address(self.token_address))

        self.assertEqual(15, balance_after - balance_before)


    def test_transfer_token(self):
        amount = 5
        l1_address, l2_address = self.load_token()

        sender_before = self.wallet.get_balance(token_address=l2_address)
        balance_before = self.zksync.zksync.zks_get_balance(
            self.address2, token_address=l2_address, block_tag=ZkBlockParams.LATEST.value
        )
        tx_hash = self.wallet.transfer(
            TransferTransaction(
                to=Web3.to_checksum_address(self.address2),
                token_address=Web3.to_checksum_address(l2_address),
                amount=amount,
            )
        )

        result = self.zksync.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertIsNotNone(result)
        sender_after = self.wallet.get_balance(token_address=l2_address)

        balance_after = self.zksync.zksync.zks_get_balance(
            self.address2, token_address=l2_address, block_tag=ZkBlockParams.LATEST.value
        )

        self.assertEqual(amount, sender_before - sender_after)
        self.assertEqual(amount ,balance_after - balance_before)

    def test_transfer_token_paymaster(self):
        amount = 5
        l1_address, l2_address = self.load_token()

        paymaster_address = self.zksync.to_checksum_address(self.paymaster_address)
        token_address = self.zksync.to_checksum_address(self.token_address)

        paymaster_balance_before = self.zksync.zksync.zks_get_balance(paymaster_address)
        paymaster_token_balance_before = self.zksync.zksync.zks_get_balance(paymaster_address,
                                                                            token_address=token_address,
                                                                            block_tag=ZkBlockParams.LATEST.value)

        sender_balance_before = self.wallet.get_balance(token_address=Web3.to_checksum_address(l2_address))
        sender_approval_token_balance_before = self.wallet.get_balance(token_address=token_address)
        reciever_balance_before = self.zksync.zksync.zks_get_balance(self.address2,
                                                                     token_address=Web3.to_checksum_address(l2_address),
                                                                     block_tag=ZkBlockParams.LATEST.value)

        paymaster_params = PaymasterParams(
            **{
                "paymaster": paymaster_address,
                "paymaster_input": self.eth_web3.to_bytes(
                    hexstr=PaymasterFlowEncoder(self.eth_web3).encode_approval_based(
                        token_address, 1, b""
                    )
                ),
            }
        )

        tx_hash = self.wallet.transfer(
            TransferTransaction(
                to=Web3.to_checksum_address(self.address2),
                token_address=Web3.to_checksum_address(l2_address),
                amount=amount,
                paymaster_params=paymaster_params
            )
        )

        self.zksync.zksync.wait_finalized(
            tx_hash, timeout=240, poll_latency=0.5
        )
        paymaster_balance_after = self.zksync.zksync.zks_get_balance(paymaster_address)
        paymaster_token_balance_after = self.zksync.zksync.zks_get_balance(paymaster_address,
                                                                           token_address=token_address,
                                                                           block_tag=ZkBlockParams.LATEST.value)

        sender_balance_after = self.wallet.get_balance(token_address=Web3.to_checksum_address(l2_address))
        sender_approval_token_balance_after = self.wallet.get_balance(token_address=token_address)
        reciever_balance_after = self.zksync.zksync.zks_get_balance(self.address2,
                                                                    token_address=Web3.to_checksum_address(l2_address),
                                                                    block_tag=ZkBlockParams.LATEST.value)

        self.assertGreaterEqual(paymaster_balance_before - paymaster_balance_after, 0)
        self.assertEqual(paymaster_token_balance_after - paymaster_token_balance_before, 1)
        self.assertEqual(sender_balance_before - sender_balance_after, 5)
        self.assertEqual(sender_approval_token_balance_before - sender_approval_token_balance_after, 1)
        self.assertEqual(reciever_balance_after - reciever_balance_before, 5)

    def test_withdraw_eth(self):
        l2_balance_before = self.wallet.get_balance()
        amount = 1

        withdraw_tx_hash = self.wallet.withdraw(
            WithdrawTransaction(
                token=Token.create_eth().l1_address, amount=Web3.to_wei(amount, "ether")
            )
        )

        self.zksync.zksync.wait_for_transaction_receipt(
            withdraw_tx_hash, timeout=240, poll_latency=0.5
        )

        l2_balance_after = self.wallet.get_balance()

        self.assertGreater(
            l2_balance_before,
            l2_balance_after,
            "L2 balance should be lower after withdrawal",
        )

    def test_withdraw_eth_paymaster(self):
        amount = 1

        paymaster_address = self.zksync.to_checksum_address(self.paymaster_address)
        token_address = self.zksync.to_checksum_address(self.token_address)

        paymaster_balance_before = self.zksync.zksync.zks_get_balance(paymaster_address)
        paymaster_token_balance_before = self.zksync.zksync.zks_get_balance(paymaster_address,
                                                                             token_address=token_address)

        sender_balance_before = self.wallet.get_balance()
        sender_approval_token_balance_before = self.wallet.get_balance(token_address=token_address)

        paymaster_params = PaymasterParams(
            **{
                "paymaster": paymaster_address,
                "paymaster_input": self.eth_web3.to_bytes(
                    hexstr=PaymasterFlowEncoder(self.eth_web3).encode_approval_based(
                        token_address, 1, b""
                    )
                ),
            }
        )

        withdraw_tx_hash = self.wallet.withdraw(
            WithdrawTransaction(
                token=Token.create_eth().l1_address,
                amount=Web3.to_wei(amount, "ether"),
                paymaster_params=paymaster_params
            )
        )

        withdraw_receipt = self.zksync.zksync.wait_finalized(
            withdraw_tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertFalse(self.wallet.is_withdrawal_finalized(withdraw_receipt["transactionHash"]))

        finalized_hash = self.wallet.finalize_withdrawal(withdraw_receipt["transactionHash"])
        self.eth_web3.eth.wait_for_transaction_receipt(
            finalized_hash, timeout=240, poll_latency=0.5
        )
        paymaster_balance_after = self.zksync.zksync.zks_get_balance(paymaster_address)
        paymaster_token_balance_after = self.zksync.zksync.zks_get_balance(paymaster_address,
                                                                           token_address=token_address)
        sender_balance_after = self.wallet.get_balance()
        sender_approval_token_balance_after = self.wallet.get_balance(token_address=token_address)

        self.assertGreater(paymaster_balance_before - paymaster_balance_after, 0)
        self.assertEqual(paymaster_token_balance_after - paymaster_token_balance_before, 1)
        self.assertEqual(sender_balance_before - sender_balance_after, Web3.to_wei(amount, "ether"))
        self.assertEqual(sender_approval_token_balance_after, sender_approval_token_balance_before - 1)

    def test_withdraw_token_paymaster(self):
        l1_address, l2_address = self.load_token()
        paymaster_address = self.zksync.to_checksum_address(self.paymaster_address)
        token_address = self.zksync.to_checksum_address(self.token_address)

        paymaster_balance_before = self.zksync.zksync.zks_get_balance(paymaster_address)
        paymaster_token_balance_before = self.zksync.zksync.zks_get_balance(paymaster_address,
                                                                            token_address=token_address,
                                                                            block_tag=ZkBlockParams.LATEST.value)
        l2_balance_before = self.wallet.get_balance(token_address=Web3.to_checksum_address(l2_address))
        l2_approval_token_balance_before = self.wallet.get_balance(token_address=token_address)

        paymaster_params = PaymasterParams(
            **{
                "paymaster": paymaster_address,
                "paymaster_input": self.eth_web3.to_bytes(
                    hexstr=PaymasterFlowEncoder(self.eth_web3).encode_approval_based(
                        token_address, 1, b""
                    )
                ),
            }
        )

        withdraw_tx_hash = self.wallet.withdraw(
            WithdrawTransaction(Web3.to_checksum_address(l2_address), 5, paymaster_params=paymaster_params)
        )

        receipt = self.zksync.zksync.wait_finalized(
            withdraw_tx_hash, timeout=240, poll_latency=0.5
        )
        self.assertFalse(self.wallet.is_withdrawal_finalized(withdraw_tx_hash))
        finalized_hash = self.wallet.finalize_withdrawal(withdraw_tx_hash)
        self.eth_web3.eth.wait_for_transaction_receipt(finalized_hash)
        paymaster_balance_after = self.zksync.zksync.zks_get_balance(paymaster_address)
        paymaster_token_balance_after = self.zksync.zksync.zks_get_balance(paymaster_address,
                                                                            token_address=token_address,
                                                                            block_tag=ZkBlockParams.LATEST.value)
        l2_balance_after = self.wallet.get_balance(
            token_address=Web3.to_checksum_address(l2_address)
        )
        l2_approval_token_balance_after = self.wallet.get_balance(token_address=token_address)

        self.assertGreaterEqual(paymaster_balance_before - paymaster_balance_after, 0)
        self.assertEqual(paymaster_token_balance_after - paymaster_token_balance_before, 1)
        self.assertIsNotNone(receipt)
        self.assertEqual(l2_approval_token_balance_before - l2_approval_token_balance_after, 1)
        self.assertEqual(l2_balance_before - l2_balance_after, 5)

    def test_withdraw_token(self):
        l1_address, l2_address = self.load_token()
        l2_balance_before = self.wallet.get_balance(
            token_address=Web3.to_checksum_address(l2_address)
        )

        withdraw_tx_hash = self.wallet.withdraw(
            WithdrawTransaction(Web3.to_checksum_address(l2_address), 5)
        )

        self.zksync.zksync.wait_for_transaction_receipt(
            withdraw_tx_hash, timeout=240, poll_latency=0.5
        )

        l2_balance_after = self.wallet.get_balance(
            token_address=Web3.to_checksum_address(l2_address)
        )

        self.assertGreater(
            l2_balance_before,
            l2_balance_after,
            "L2 balance should be lower after withdrawal",
        )

    def test_get_request_execute_transaction(self):
        result = self.wallet.get_request_execute_transaction(
            RequestExecuteCallMsg(
                contract_address=self.zksync_contract.address,
                call_data=HexStr("0x"),
                l2_value=7_000_000_000,
            )
        )

        self.assertIsNotNone(result)

    def test_estimate_request_execute(self):
        result = self.wallet.estimate_gas_request_execute(
            RequestExecuteCallMsg(
                contract_address=self.zksync_contract.address,
                call_data=HexStr("0x"),
                l2_value=7_000_000_000,
            )
        )

        self.assertGreater(result, 0)

    def test_request_execute(self):
        amount = 1
        l2_balance_before = self.wallet.get_balance()

        tx_hash = self.wallet.request_execute(
            RequestExecuteCallMsg(
                contract_address=Web3.to_checksum_address(
                    self.zksync.zksync.main_contract_address
                ),
                call_data=HexStr("0x"),
                l2_value=amount,
                l2_gas_limit=900_000,
            )
        )
        l1_tx_receipt = self.eth_web3.eth.wait_for_transaction_receipt(tx_hash)
        l2_hash = self.zksync.zksync.get_l2_hash_from_priority_op(
            l1_tx_receipt, self.zksync_contract
        )
        self.zksync.zksync.wait_for_transaction_receipt(l2_hash)
        l2_balance_after = self.wallet.get_balance()
        self.assertEqual(
            1, l1_tx_receipt["status"], "L1 transaction should be successful"
        )
        self.assertGreaterEqual(
            l2_balance_after - l2_balance_before,
            amount,
            "Balance on L2 should be increased",
        )