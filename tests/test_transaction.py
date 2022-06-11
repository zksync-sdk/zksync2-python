from unittest import TestCase
from eip712_structs import make_domain
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from eth_utils.crypto import keccak_256
from hexbytes import HexBytes
from web3 import Web3
from transaction.transaction import Withdraw
from zk_types.zk_types import Token, Fee, TokenAddress


class TestTransactionRequest(TestCase):
    PRIVATE_KEYS = ['0xa045b52470d306ff78e91b0d2d92f90f7504189125a46b69423dc673fd6b4f3e',
                    '0x601b47729b2820e94bc10125edc8d534858827428b449175a275069dc00c303f',
                    '0xa7adf8459b4c9a62f09e0e5390983c0145fa20e88c9e5bf837d8bf3dcd05bd9c']

    _RECEIVER = HexStr("0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC")
    _NONCE = 42
    _DEFAULT_ADDRESS_STR = "0" * 40

    def setUp(self) -> None:
        self.account: LocalAccount = Account.from_key(self.PRIVATE_KEYS[0])
        self.fee_token = Token.create_eth()
        self.fee = Fee(
            feeToken=TokenAddress(self.fee_token.address),
            ergsLimit=HexBytes(123),
            ergsPriceLimit=HexBytes(123),
            ergsPerStorageLimit=HexBytes(123),
            ergsPerPubdataLimit=HexBytes(123)
        )
        self.withdraw = Withdraw(token_address=self.fee_token.address,
                                 to=self._RECEIVER,
                                 amount=Web3.toWei(1, 'ether'),
                                 initiator_address=self.account.address,
                                 fee=self.fee,
                                 nonce=self._NONCE
                                 )
        self.default_domain = make_domain(name="zkSync",
                                          version=2,
                                          chainId=42,
                                          verifyingContract=self._DEFAULT_ADDRESS_STR)

    def test_encode_type(self):
        transaction_request = self.withdraw.transaction_request()
        type_description = transaction_request.encode_type()
        self.assertEqual('TransactionRequest(address to,uint256 nonce,uint256 value,bytes data,uint256'
                         ' gasPrice,uint256 gasLimit,uint256 ergsPerStorage,uint256'
                         ' ergsPerPubdata,address feeToken,address withdrawToken)',
                         type_description)

    def test_encode_value(self):
        transaction_request = self.withdraw.transaction_request()
        type_hash = transaction_request.type_hash()
        value_hash = transaction_request.encode_value()
        intermediate = type_hash + value_hash
        ret = keccak_256(intermediate)
        self.assertEqual('aa6ad134be006ef5c644699e8bed3cc8ba1e7e3959ac16bca67fe966d1933d3b', ret.hex())

    def test_encode_data(self):
        transaction_request = self.withdraw.transaction_request()
        bytes_result = transaction_request.signable_bytes(self.default_domain)
        bytes_hash = keccak_256(bytes_result)
        self.assertEqual("920215621a903192bf987305c42025dc6a4376ba01a97dd93dc327758fa407aa", bytes_hash.hex())
