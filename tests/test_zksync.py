from eth_typing import HexStr, ChecksumAddress, HexAddress
from hexbytes import HexBytes
from protocol.zksync import ZkSyncBuilder
from unittest import TestCase
from zk_types.zk_types import Transaction, Eip712Meta, L1WithdrawHash, TokenAddress
from decimal import Decimal
from eth_typing import Address


class TestZkSync(TestCase):
    URL_TESTNET = "https://zksync2-testnet.zksync.dev"
    TOKEN_ADDRESS = TokenAddress(HexStr('0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'))
    _TEST_ADDRESS_HEX = "0xc94770007dda54cF92009BFF0dE90c06F603a09f"
    TEST_ADDRESS = Address(bytearray.fromhex(_TEST_ADDRESS_HEX[2:]))

    def setUp(self) -> None:
        self.web3 = ZkSyncBuilder.build(self.URL_TESTNET)

    def test_zks_main_contract(self):
        main_contract = self.web3.zksync.zks_main_contract()
        self.assertEqual(main_contract, '0x0e9b63a28d26180dbf40e8c579af3abf98ae05c5')

    # def test_zks_estimate_fee(self):
    #     """
    #     # ValueError: {'code': 3, 'message': 'Execution error', 'data': {'code': 104, 'message': 'Not enough balance to cover the fee. Balance: 0, fee: 304000000000000000'}}
    #     """
    #     eip: Eip712Meta = {
    #         "feeToken": HexStr("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"),
    #         "ergsPerStorage": HexStr(HexBytes(0).hex()),
    #         "ergsPerPubdata": HexStr(HexBytes(0).hex())
    #     }
    #     tx: Transaction = {
    #         "from": HexStr("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"),
    #         "to":  HexStr("0xd46e8dd67c5d32be8058bb8eb970870f07244567"),
    #         "gas": HexStr("0x76c0"),
    #         "gasPrice": HexStr("0x9184e72a000"),
    #         # "value": HexStr("0x9184e72a"),
    #         "value": HexStr("0x0"),
    #         "data": HexStr("0xd46e8dd67c5d32be8d46e8dd67c5d32be8058bb8eb970870f072445675058bb8eb970870f072445675"),
    #         "transactionType": HexStr("0x70"),
    #         "eip712Meta": eip
    #     }
    #
    #     response = self.web3.zksync.zks_estimate_fee(tx)
    #     self.assertEqual(response['ergsLimit'], "0x2940")
    #     self.assertEqual(response['ergsPriceLimit'], "0x6f9c")

    def test_zks_get_l1_withdraw_tx(self):
        """
        result: b'{"jsonrpc":"2.0","result":null,"id":0}' TODO: check it
        """
        l1_withdraw_hash = HexStr("0x871567b0c7ee50460771ace2a88d1ac7bc785c9e3a22e2b193c45892a52e3359")
        response = self.web3.zksync.zks_get_l1_withdraw_tx(l1_withdraw_hash)
        self.assertEqual(response, None)

    def test_zks_get_account_transactions(self):
        lst = self.web3.zksync.zks_get_account_transactions("0x7e5f4552091a69125d5dfcb7b8c2659029395bdf", 0, 100)
        trans = lst[0]
        self.assertEqual(trans['blockHash'], '0x1abde51c998b474ebbe3ff5298acad2a97b4bafa12500fa3e944150f12f2e0e2')
        self.assertEqual(trans['blockNumber'], '0x7f20b')
        self.assertEqual(trans['transactionIndex'], '0x5')

    def test_zks_get_confirmed_tokens(self):
        response = self.web3.zksync.zks_get_confirmed_tokens(0, 10)
        mapped_result = {obj['address']: obj for obj in response}
        obj = mapped_result[self.TOKEN_ADDRESS]
        self.assertEqual(obj['name'], 'ETH')
        self.assertEqual(obj['symbol'], 'ETH')

    def test_zks_is_token_liquid(self):
        response = self.web3.zksync.zks_is_token_liquid(self.TOKEN_ADDRESS)
        self.assertTrue(response)

    def test_zks_get_token_price(self):
        """
        INFO: double format is significant, it could change
        """
        response = self.web3.zksync.zks_get_token_price(self.TOKEN_ADDRESS)
        price = Decimal(response)
        self.assertEqual(price, Decimal('3500.00'))

    def test_zks_l1_chain_id(self):
        response = self.web3.zksync.zks_l1_chain_id()
        self.assertEqual(response, '0x5')

    def test_eth_get_balance(self):
        token_address = TokenAddress(HexStr("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"))
        balance = self.web3.zksync.eth_get_balance(self.TEST_ADDRESS, "latest", token_address)
        self.assertEqual(balance, 0)
