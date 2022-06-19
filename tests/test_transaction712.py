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
    _TEST_CHAIN_ID = 270
    _DEFAULT_NONCE = 0

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

    # def test_encode_execute(self):
    #     execute = Execute(contract_address=HexStr("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"),
    #                       call_data=)
