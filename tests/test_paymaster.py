from decimal import Decimal
from unittest import TestCase, skip
from eth_typing import HexStr
from eth_utils import keccak
from web3 import Web3
from zksync2.module.request_types import create2_contract_transaction
from zksync2.manage_contracts.gas_provider import StaticGasProvider
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.core.types import Token, EthBlockParams
from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from tests.contracts.utils import get_binary
from zksync2.transaction.transaction712 import Transaction712


class PaymasterTests(TestCase):
    GAS_LIMIT = 21000
    ETH_TEST_URL = "https://goerli.infura.io/v3/25be7ab42c414680a5f89297f8a11a4d"
    ZKSYNC_TEST_URL = "https://zksync2-testnet.zksync.dev"

    ETH_TOKEN = Token.create_eth()
    # PRIVATE_KEY = b'\00' * 31 + b'\02'
    PRIVATE_KEY = bytes.fromhex("1f0245d47b3a84299aeb121ac33c2dbd1cdb3d3c2079b3240e63796e75ee8b70")
    ETH_AMOUNT_BALANCE = 1
    ETH_TEST_NET_AMOUNT_BALANCE = Decimal(1)
    SALT = keccak(text="TestPaymaster")

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.ZKSYNC_TEST_URL)
        self.account: LocalAccount = Account.from_key(self.PRIVATE_KEY)
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        self.gas_provider = StaticGasProvider(Web3.toWei(1, "gwei"), 555000)

    @skip("Integration test, paymaster params test not implemented yet")
    def test_deploy_paymaster(self):
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        precomputed_address: HexStr = self.web3.zksync.zks_get_testnet_paymaster_address()
        constructor = b''
        custom_paymaster_bin = get_binary("custom_paymaster.bin")
        tx = create2_contract_transaction(web3=self.web3,
                                          from_=self.account.address,
                                          ergs_price=0,
                                          ergs_limit=0,
                                          bytecode=custom_paymaster_bin,
                                          call_data=constructor,
                                          salt=self.SALT)
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx)
        gas_price = self.web3.zksync.gas_price
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = Transaction712(chain_id=self.chain_id,
                                nonce=nonce,
                                gas_limit=estimate_gas,
                                to=tx["to"],
                                value=Web3.toWei(0.01, 'ether'),
                                data=tx["data"],
                                maxPriorityFeePerGas=100000000,
                                maxFeePerGas=gas_price,
                                from_=self.account.address,
                                meta=tx["eip712Meta"])

        eip712_structured = tx_712.to_eip712_struct()
        singed_message = self.signer.sign_typed_data(eip712_structured)
        msg = tx_712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

        contract_address = tx_receipt["contractAddress"]
        self.assertEqual(precomputed_address.lower(), contract_address)
