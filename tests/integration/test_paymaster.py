from decimal import Decimal
from pathlib import Path
from unittest import TestCase, skip
from eth_typing import HexStr
from eth_utils import keccak, remove_0x_prefix
from web3 import Web3

from tests.integration.test_config import LOCAL_ENV
from tests.integration.test_zksync_contract import generate_random_salt
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder, JsonConfiguration
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.nonce_holder import _nonce_holder_abi_default
from zksync2.manage_contracts.paymaster_utils import PaymasterFlowEncoder
from zksync2.manage_contracts.erc20_contract import ERC20Contract, get_erc20_abi
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.core.types import Token, EthBlockParams, ZkBlockParams, PaymasterParams
from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from tests.contracts.utils import contract_path
from zksync2.transaction.transaction_builders import TxFunctionCall, TxCreate2Contract, TxCreateAccount


# mint tx hash of Test coins:
# https://goerli.explorer.zksync.io/address/0xFC174650BDEbE4D94736442307D4D7fdBe799EeC#contract

class PaymasterTests(TestCase):

    ETH_TOKEN = Token.create_eth()
    PRIVATE_KEY = bytes.fromhex("1f0245d47b3a84299aeb121ac33c2dbd1cdb3d3c2079b3240e63796e75ee8b70")
    ETH_AMOUNT_BALANCE = 1
    ETH_TEST_NET_AMOUNT_BALANCE = Decimal(1)

    SERC20_TOKEN = Token(
        Web3.to_checksum_address("0x" + "0" * 40),
        Web3.to_checksum_address("0xFC174650BDEbE4D94736442307D4D7fdBe799EeC"),
        "SERC20",
        18)

    SALT = keccak(text="TestPaymaster")

    def setUp(self) -> None:
        self.env = LOCAL_ENV
        self.web3 = ZkSyncBuilder.build(self.env.zksync_server)
        self.account: LocalAccount = Account.from_key("0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110")
        self.chain_id = self.web3.zksync.chain_id
        self.signer = PrivateKeyEthSigner(self.account, self.chain_id)
        #self.custom_paymaster = ContractEncoder.from_json(self.web3, contract_path("CustomPaymaster.json"))

    def _is_deployed(self):
        return len(self.web3.zksync.get_code(self.paymaster_address)) > 0

    @property
    def paymaster_address(self) -> HexStr:
        return self.web3.zksync.zks_get_testnet_paymaster_address()

    def deploy_paymaster(self, token_address):
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Paymaster.json")
        token_address = self.web3.to_checksum_address(token_address)
        constructor_arguments = {"_erc20": token_address}

        chain_id = self.web3.zksync.chain_id
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.PENDING.value
        )
        nonce_holder = self.web3.zksync.contract(address=ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value,
                                               abi=_nonce_holder_abi_default())
        deployment_nonce = nonce_holder.functions.getDeploymentNonce(self.account.address).call(
            {
                "from": self.account.address
            })
        deployer = PrecomputeContractDeployer(self.web3)
        precomputed_address = deployer.compute_l2_create_address(self.account.address, deployment_nonce)
        token_contract = ContractEncoder.from_json(self.web3, path.resolve(), JsonConfiguration.STANDARD)
        encoded_constructor = token_contract.encode_constructor(**constructor_arguments)
        gas_price = self.web3.zksync.gas_price
        create_account = TxCreateAccount(
            web3=self.web3,
            chain_id=chain_id,
            nonce=nonce,
            from_=self.account.address,
            gas_price=gas_price,
            bytecode=token_contract.bytecode,
            call_data=encoded_constructor,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(create_account.tx)
        tx_712 = create_account.tx712(estimate_gas)
        signed_message = self.signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(signed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        return tx_receipt["contractAddress"]

    def test_paymaster(self):
        directory = Path(__file__).parent
        path = directory / Path("../contracts/Token.json")
        constructor_arguments = {"name_": "Ducat", "symbol_": "Ducat", "decimals_": 18}
        chain_id = self.web3.zksync.chain_id
        signer = PrivateKeyEthSigner(self.account, chain_id)
        nonce = self.web3.zksync.get_transaction_count(
            self.account.address, EthBlockParams.PENDING.value
        )
        random_salt = generate_random_salt()
        token_contract = ContractEncoder.from_json(self.web3, path.resolve(), JsonConfiguration.STANDARD)
        abi = token_contract.abi
        encoded_constructor = token_contract.encode_constructor(**constructor_arguments)

        gas_price = self.web3.zksync.gas_price
        create2_contract = TxCreate2Contract(web3=self.web3,
                                             chain_id=chain_id,
                                             nonce=nonce,
                                             from_=self.account.address,
                                             gas_limit=0,
                                             gas_price=gas_price,
                                             bytecode=token_contract.bytecode,
                                             salt=random_salt,
                                             call_data=encoded_constructor)
        estimate_gas = self.web3.zksync.eth_estimate_gas(create2_contract.tx)
        tx_712 = create2_contract.tx712(estimate_gas)
        signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(signed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )
        token_contract_address = tx_receipt["contractAddress"]
        token_contract = self.web3.zksync.contract(token_contract_address, abi=abi)

        mint_tx = token_contract.functions.mint(self.account.address, 15).build_transaction({
            "nonce": self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value),
            "from": self.account.address,
            "maxPriorityFeePerGas": 1_000_000,
            "maxFeePerGas": self.web3.zksync.gas_price,
        })

        signed = self.account.sign_transaction(mint_tx)
        tx_hash = self.web3.zksync.send_raw_transaction(signed.rawTransaction)
        self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )

        paymaster_address = self.deploy_paymaster(token_contract_address)

        tx_func_call = TxFunctionCall(
            chain_id=self.web3.zksync.chain_id,
            nonce=self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value),
            from_=self.account.address,
            to=paymaster_address,
            value=self.web3.to_wei(1, "ether"),
            data=HexStr("0x"),
            gas_limit=0,  # Unknown at this state, estimation is done in next step
            gas_price=gas_price,
            max_priority_fee_per_gas=100_000_000,
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx_func_call.tx)
        tx_712 = tx_func_call.tx712(estimate_gas)
        signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(signed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )

        calladata = token_contract.encodeABI(fn_name="mint", args=[self.account.address, 7])

        paymaster_params = PaymasterParams(**{
            "paymaster": paymaster_address,
            "paymaster_input": self.web3.to_bytes(
                hexstr=PaymasterFlowEncoder(self.web3).encode_approval_based(token_contract_address, 1, b''))
        })

        tx_func_call = TxFunctionCall(
            chain_id=self.web3.zksync.chain_id,
            nonce=self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.LATEST.value),
            from_=self.account.address,
            to=token_contract_address,
            data=calladata,
            gas_limit=0,  # Unknown at this state, estimation is done in next step
            gas_price=gas_price,
            max_priority_fee_per_gas=100_000_000,
            paymaster_params=paymaster_params
        )
        estimate_gas = self.web3.zksync.eth_estimate_gas(tx_func_call.tx)
        tx_712 = tx_func_call.tx712(estimate_gas)
        signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(signed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)

        self.web3.zksync.wait_for_transaction_receipt(
            tx_hash, timeout=240, poll_latency=0.5
        )

    @skip("Integration test, paymaster params test not implemented yet")
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
                                                bytecode=self.custom_paymaster.bytecode,
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

    def get_balance(self, addr: HexStr, token: Token, at: EthBlockParams = EthBlockParams.LATEST):
        if token.is_eth():
            return self.web3.zksync.get_balance(addr, at.value)
        else:
            erc20 = ERC20Contract(self.web3.zksync,
                                  contract_address=token.l2_address,
                                  account=self.account)
            return erc20.balance_of(addr)

    @skip("Integration test, paymaster params test not implemented yet")
    def test_send_funds_for_fee(self):
        gas_price = self.web3.zksync.gas_price
        func_call = TxFunctionCall(self.chain_id,
                                   nonce=0,
                                   from_=self.account.address,
                                   to=self.paymaster_address,
                                   gas_price=gas_price)
        estimate_gas = self.web3.zksync.eth_estimate_gas(func_call.tx)
        fee = estimate_gas * gas_price
        print(f"Fee : {fee}")
        serc20_balance = self.get_balance(self.account.address, self.SERC20_TOKEN)
        print(f"SERC20 balance: {serc20_balance}")

        self.assertTrue(serc20_balance >= fee, f"Not enough balance for pay fee {fee} with balance {serc20_balance}")

        nonce = self.web3.zksync.get_transaction_count(self.account.address, ZkBlockParams.COMMITTED.value)
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

    def build_paymaster(self, trans: TxFunctionCall, fee: int) -> TxFunctionCall:
        paymaster_encoder = PaymasterFlowEncoder(self.web3)
        encoded_approval_base = paymaster_encoder.encode_approval_based(self.SERC20_TOKEN.l2_address,
                                                                        fee,
                                                                        b'')
        encoded_approval_bin = bytes.fromhex(remove_0x_prefix(encoded_approval_base))
        trans.tx["eip712Meta"].paymaster_params = PaymasterParams(paymaster=self.paymaster_address,
                                                                  paymaster_input=encoded_approval_bin)
        return trans

    @skip("Integration test, paymaster params test not implemented yet")
    def test_send_funds_with_paymaster(self):
        gas_price = self.web3.zksync.gas_price
        paymaster_address = self.paymaster_address
        nonce = self.web3.zksync.get_transaction_count(self.account.address, EthBlockParams.PENDING.value)
        transaction = TxFunctionCall(self.chain_id,
                                     nonce=nonce,
                                     from_=self.account.address,
                                     to=self.account.address,
                                     gas_price=gas_price)

        # INFO: encode paymaster params with dummy fee to estimate real one
        unknown_fee = 0
        transaction = self.build_paymaster(transaction, unknown_fee)

        paymaster_est_gas = self.web3.zksync.eth_estimate_gas(transaction.tx)
        preprocessed_fee = gas_price * paymaster_est_gas

        print(f"Paymaster fee: {preprocessed_fee}")

        erc20 = ERC20Contract(self.web3.zksync, contract_address=self.SERC20_TOKEN.l2_address,
                              account=self.account)

        allowance = erc20.allowance(self.account.address, paymaster_address)
        if allowance < preprocessed_fee:
            is_approved = erc20.approve(paymaster_address,
                                        preprocessed_fee,
                                        gas_limit=paymaster_est_gas)
            self.assertTrue(is_approved)

        # INFO: encode paymaster params with real fee
        transaction = self.build_paymaster(transaction, preprocessed_fee)

        balance_before = self.web3.zksync.get_balance(self.account.address, EthBlockParams.PENDING.value)
        print(f"balance before : {balance_before}")

        tx712 = transaction.tx712(paymaster_est_gas)
        singed_message = self.signer.sign_typed_data(tx712.to_eip712_struct())
        msg = tx712.encode(singed_message)
        tx_hash = self.web3.zksync.send_raw_transaction(msg)
        tx_receipt = self.web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        self.assertEqual(1, tx_receipt["status"])

        balance_after = self.web3.zksync.get_balance(self.account.address, EthBlockParams.PENDING.value)
        print(f"balance after: {balance_after}")

        self.assertEqual(balance_before, balance_after)
