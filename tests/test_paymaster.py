from decimal import Decimal
from unittest import TestCase, skip
from eth_typing import HexStr
from eth_utils import keccak, remove_0x_prefix
from web3 import Web3
from web3.middleware import geth_poa_middleware
from zksync2.provider.eth_provider import EthereumProvider

from zksync2.manage_contracts.paymaster_utils import PaymasterFlowEncoder
from zksync2.manage_contracts.erc20_contract import ERC20Contract
from zksync2.manage_contracts.gas_provider import StaticGasProvider
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.core.types import Token, EthBlockParams, ZkBlockParams, PaymasterParams
from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from tests.contracts.utils import get_hex_binary
from zksync2.transaction.transaction712 import TxCreate2Contract, TxFunctionCall


class PaymasterTests(TestCase):
    ETH_TEST_URL = "https://rpc.ankr.com/eth_goerli"
    ZKSYNC_TEST_URL = "https://zksync2-testnet.zksync.dev"

    ETH_TOKEN = Token.create_eth()
    PRIVATE_KEY = bytes.fromhex("1f0245d47b3a84299aeb121ac33c2dbd1cdb3d3c2079b3240e63796e75ee8b70")
    ETH_AMOUNT_BALANCE = 1
    ETH_TEST_NET_AMOUNT_BALANCE = Decimal(1)
    USDC_TOKEN = Token(
        Web3.toChecksumAddress("0xd35cceead182dcee0f148ebac9447da2c4d449c4"),
        Web3.toChecksumAddress("0x72c4f199cb8784425542583d345e7c00d642e345"),
        "USDC",
        6)
    SALT = keccak(text="TestPaymaster")

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.ZKSYNC_TEST_URL)
        self.account: LocalAccount = Account.from_key(self.PRIVATE_KEY)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.gas_provider = StaticGasProvider(Web3.toWei(1, "gwei"), 555000)

        self.custom_paymaster_contract_bin = get_hex_binary("custom_paymaster_binary.hex")

    def test_deposit_usdc(self):
        print(f"gas price: {self.web3.eth.gas_price}")
        amount_usdc = 100000
        eth_web3 = Web3(Web3.HTTPProvider(self.ETH_TEST_URL))
        eth_web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        eth_provider = EthereumProvider.build_ethereum_provider(zksync=self.web3,
                                                                eth=eth_web3,
                                                                account=self.account,
                                                                gas_provider=self.gas_provider)
        ret = eth_provider.approve_deposits(self.USDC_TOKEN, amount_usdc)
        print(f"approve deposit: {ret}")
        tx_receipt = eth_provider.deposit(self.USDC_TOKEN,
                                          amount_usdc,
                                          self.account.address)
        self.assertEqual(1, tx_receipt["status"])

    def _is_deployed(self):
        return len(self.web3.zksync.get_code(self.paymaster_address)) > 0

    @property
    def paymaster_address(self) -> HexStr:
        return self.web3.zksync.zks_get_testnet_paymaster_address()

    # @skip("Integration test, paymaster params test not implemented yet")
    def test_deploy_paymaster(self):
        if not self._is_deployed():
            nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
            precomputed_address: HexStr = self.web3.zksync.zks_get_testnet_paymaster_address()
            gas_price = self.web3.zksync.gas_price

            constructor = b''
            create_contract = TxCreate2Contract(web3=self.web3,
                                                chain_id=self.chain_id,
                                                nonce=nonce,
                                                from_=self.account.address,
                                                gas_limit=0,
                                                gas_price=gas_price,
                                                bytecode=self.custom_paymaster_contract_bin,
                                                call_data=constructor,
                                                salt=self.SALT)

            estimate_gas = self.web3.zksync.eth_estimate_gas(create_contract.tx)
            gas_price = self.web3.zksync.gas_price
            print(f"Fee for transaction is: {estimate_gas * gas_price}")

            tx_712 = create_contract.tx712(estimate_gas)
            eip712_structured = tx_712.to_eip712_struct()
            singed_message = self.signer.sign_typed_data(eip712_structured)
            msg = tx_712.encode(singed_message)
            tx_hash = self.web3.zksync.send_raw_transaction(msg)
            tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
            self.assertEqual(1, tx_receipt["status"])

            contract_address = tx_receipt["contractAddress"]
            self.assertEqual(precomputed_address.lower(), contract_address)
        else:
            print("Skipping test, contract is already deployed")

    def send_funds_for_fee(self):
        gas_price = self.web3.zksync.gas_price
        func_call = TxFunctionCall(self.chain_id,
                                   nonce=0,
                                   from_=self.account.address,
                                   to=self.paymaster_address,
                                   gas_price=gas_price)
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        fee = estimate_gas * gas_price
        print(f"Fee : {fee}")

        token_contract = ERC20Contract(web3=self.web3,
                                       contract_address=self.USDC_TOKEN.l2_address,
                                       account=self.account)
        usdc_balance = token_contract.balance_of(self.account.address)
        print(f"USDC balance: {usdc_balance}")

        self.assertTrue(usdc_balance >= fee, f"Not enough balance for pay fee {fee} with balance {usdc_balance}")

        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED)
        transfer_for_fee = TxFunctionCall(chain_id=self.chain_id,
                                          nonce=nonce,
                                          from_=self.account.address,
                                          to=self.paymaster_address,
                                          value=fee,
                                          gas_price=gas_price,
                                          gas_limit=0)
        est_gas = self.web3.zksync.eth_estimate_gas(transfer_for_fee.tx)
        tx712 = transfer_for_fee.tx712(est_gas)
        singed_message = self.signer.sign_typed_data(tx712.to_eip712_struct())
        msg = tx712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

    def send_funds_with_paymaster(self):
        gas_price = self.web3.zksync.gas_price
        paymaster_address = self.paymaster_address

        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        transaction = TxFunctionCall(self.chain_id,
                                     nonce=nonce,
                                     from_=self.account.address,
                                     to=self.account.address,
                                     gas_price=gas_price)
        est_gas = self.web3.zksync.eth_estimate_gas(transaction.tx)
        fee = est_gas * gas_price
        balance = self.web3.zksync.get_balance(paymaster_address, EthBlockParams.LATEST)
        self.assertTrue(balance > fee, "Not enough balance to process fee")

        erc20 = ERC20Contract(self.web3, contract_address=self.USDC_TOKEN.l2_address, account=self.account)

        allowance = erc20.allowance(self.account.address, paymaster_address)
        if allowance < fee:
            tx_receipt = erc20.approve_deposit(paymaster_address, fee)
            self.assertEqual(1, tx_receipt["status"])

        balance_before = self.web3.zksync.get_balance(self.account.address, EthBlockParams.PENDING)
        paymaster_encoder = PaymasterFlowEncoder(self.web3)
        encoded_approval_base = paymaster_encoder.encode_approval_based(self.USDC_TOKEN.l2_address,
                                                                        fee,
                                                                        b'')
        encoded_approval_bin = bytes.fromhex(remove_0x_prefix(encoded_approval_base))
        transaction.tx["eip712Meta"].paymaster_params = PaymasterParams(paymaster=paymaster_address,
                                                                        paymaster_input=encoded_approval_bin)
        tx712 = transaction.tx712(est_gas)
        singed_message = self.signer.sign_typed_data(tx712.to_eip712_struct())
        msg = tx712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

        balance_after = self.web3.zksync.get_balance(self.account.address, EthBlockParams.PENDING)
        self.assertEqual(balance_before, balance_after)

