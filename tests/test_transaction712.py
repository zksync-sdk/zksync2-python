from unittest import TestCase
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3
from zk_types.zk_types import Token, Fee, TokenAddress

from transaction.transaction import TransactionBase, TransactionType, Withdraw
from transaction.transaction712 import Transaction712


class TestTransaction712(TestCase):
    _DEFAULT_ADDRESS_STR = "0" * 40
    _TEST_ADDRESS = HexStr("0x7e5f4552091a69125d5dfcb7b8c2659029395bdf")

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

    def test_withdraw_encode(self):
        withdraw = Withdraw(token_address=self.token.address,
                            to=self._TEST_ADDRESS,
                            amount=Web3.toWei(1, 'ether'),
                            initiator_address=self.account.address,
                            fee=self.fee, nonce=0)
        tx712 = Transaction712(withdraw, 270)
        ret = tx712.as_rlp_values()
        ret = Transaction712.EIP_712_TX_TYPE + ret
        self.assertEqual("70f852808080947e5f4552091a69125d5dfcb7b8c2659029395bdf880de0b6b3a76400008082010e94"
                         "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee94eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee8080c0",
                         ret.hex())
