from unittest import TestCase
from eth_typing import HexStr
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from eth_account.signers.local import LocalAccount
from eth_account import Account
from eip712_structs import make_domain, EIP712Struct, String, Address
from eth_utils.crypto import keccak_256


class Person(EIP712Struct):
    name = String()
    wallet = Address()


class Mail(EIP712Struct):
    pass


def make_mail(from_, to, content) -> Mail:
    setattr(Mail, 'from', Person)
    setattr(Mail, 'to', Person)
    setattr(Mail, 'contents', String())

    kwargs = {
        'to': to,
        'from': from_,
        'contents': content
    }
    return Mail(**kwargs)


class TestEthSigner(TestCase):
    _TEST_TYPED_EXPECTED_SIGNATURE = HexStr("0x4355c47d63924e8a72e509b65029052eb6c299d53a04e167c5775fd466751"
                                            "c9d07299936d304c153f6443dfa05f40ff007d72911b6f72307f996231605b915621c")

    def setUp(self) -> None:
        self.domain = make_domain(name="Ether Mail",
                                  version="1",
                                  chainId=1,
                                  verifyingContract="0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC")
        self.person_from = Person(name="Cow", wallet="0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826")
        self.person_to = Person(name="Bob", wallet="0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB")
        self.mail = make_mail(from_=self.person_from, to=self.person_to, content="Hello, Bob!")

        private_key = keccak_256("cow".encode('utf-8'))
        self.account: LocalAccount = Account.from_key(private_key)
        self.signer = PrivateKeyEthSigner(self.account, 1)

    def test_sign_typed_data(self):
        sm = self.signer.sign_typed_data(self.mail, self.domain)
        self.assertEqual(self._TEST_TYPED_EXPECTED_SIGNATURE, sm.signature.hex())

    def test_verify_signed_typed_data(self):
        ret = self.signer.verify_typed_data(self._TEST_TYPED_EXPECTED_SIGNATURE, self.mail, self.domain)
        self.assertTrue(ret)
