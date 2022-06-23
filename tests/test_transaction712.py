import json
from unittest import TestCase
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3
from zk_types.zk_types import Token, Fee, TokenAddress
from pathlib import Path

from transaction.transaction import Withdraw, DeployContract, Execute
from transaction.transaction712 import Transaction712


class TestTransaction712(TestCase):
    _DEFAULT_ADDRESS_STR = "0" * 40
    _TEST_ADDRESS = HexStr("0x7e5f4552091a69125d5dfcb7b8c2659029395bdf")
    _EXECUTE_INITIATE_ADDRESS = HexStr("0xe1fab3efd74a77c23b426c302d96372140ff7d0c")
    _TEST_CHAIN_ID = 270
    _DEFAULT_NONCE = 0
    _INCREMENT_FUNCTION_NAME = 'increment'

    def setUp(self) -> None:
        self.account: LocalAccount = Account.create(1)
        self.token = Token.create_eth()

        self.fee = Fee(
            feeToken=TokenAddress(self.token.address),
            ergsLimit=HexBytes(0),
            ergsPriceLimit=HexBytes(0),
            ergsPerStorageLimit=HexBytes(0),
            ergsPerPubdataLimit=HexBytes(0)
        )
        p = Path('./counter_contract.hex')
        with p.open(mode='r') as contact_file:
            lines = contact_file.readlines()
            data = "".join(lines)
            self.counter_contract = bytes.fromhex(data)
        p = Path('deploy_contract712_expected.txt')
        with p.open(mode='r') as deploy_expected_file:
            lines = deploy_expected_file.readlines()
            self.deploy_contract_expected = "".join(lines)

        p = Path('./counter_contract_abi.json')
        with p.open(mode='r') as json_f:
            self.counter_contract_abi = json.load(json_f)
        self.w3 = Web3(Web3.EthereumTesterProvider())
        self.counter_contract_instance = self.w3.eth.contract(abi=self.counter_contract_abi,
                                                              bytecode=self.counter_contract)

    def test_withdraw_encode(self):
        withdraw = Withdraw(token_address=self.token.address,
                            to=self._TEST_ADDRESS,
                            amount=Web3.toWei(1, 'ether'),
                            initiator_address=self.account.address,
                            fee=self.fee, nonce=self._DEFAULT_NONCE)
        tx712 = Transaction712(withdraw, self._TEST_CHAIN_ID)
        ret = tx712.as_rlp_values()
        ret = Transaction712.EIP_712_TX_TYPE + ret
        self.assertEqual("70f852808080947e5f4552091a69125d5dfcb7b8c2659029395bdf880de0b6b3a76400008082010e94"
                         "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee94eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee8080c0",
                         ret.hex())

    def test_encode_deploy(self):
        deploy_contract = DeployContract(self.counter_contract,
                                         call_data=None,
                                         initiator_address=self.account.address,
                                         fee=self.fee,
                                         nonce=0)
        tx712 = Transaction712(deploy_contract, self._TEST_CHAIN_ID)
        ret = tx712.as_rlp_values()
        ret = Transaction712.EIP_712_TX_TYPE + ret
        self.assertEqual(self.deploy_contract_expected, ret.hex())

    def test_encode_execute(self):
        encoded_function = self.counter_contract_instance.encodeABI(fn_name=self._INCREMENT_FUNCTION_NAME, args=[42])
        contract_addr = HexStr("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        if encoded_function.startswith("0x"):
            encoded_function = encoded_function[2:]
        execute = Execute(contract_address=contract_addr,
                          call_data=bytes.fromhex(encoded_function),
                          initiator_address=self._EXECUTE_INITIATE_ADDRESS,
                          fee=self.fee, nonce=0)
        tx712 = Transaction712(execute, self._TEST_CHAIN_ID)
        ret = tx712.as_rlp_values()
        ret = Transaction712.EIP_712_TX_TYPE + ret
        self.assertEqual("70f85a80808094eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee80a47cf5dab"
                         "0000000000000000000000000000000000000000000000000000000000000002a"
                         "82010e94eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee808080c0", ret.hex())
