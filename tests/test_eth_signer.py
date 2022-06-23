from unittest import TestCase

from eth_typing import HexStr

from crypto.eth_signer import PrivateKeyEthSigner
from eth_account.signers.local import LocalAccount
from eth_account import Account
from hexbytes import HexBytes
from eip712_structs import make_domain, EIP712Struct, String, Address
from eth_utils.crypto import keccak_256


def random_key_generator(s: int):
    """
    INFO: Use it for test key generation
    """
    import random
    import string
    char_set = string.hexdigits + string.digits
    return ''.join(random.sample(char_set * s, s))


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
    _TEST_PRIVATE_KEY = "0x119dB1AfDBB7Be947Cfb340035e306b64E982E0C5eC63045786c9C7AfB56d560"
    _TEST_TYPED_EXPECTED_SIGNATURE = HexStr("0x4355c47d63924e8a72e509b65029052eb"
                                            "6c299d53a04e167c5775fd466751c9d07299"
                                            "936d304c153f6443dfa05f40ff007d72911b6f72307f996231605b915621c")

    def setUp(self) -> None:
        account: LocalAccount = Account.from_key(self._TEST_PRIVATE_KEY)
        self.signer = PrivateKeyEthSigner(account, 5)

        self.domain = make_domain(name="Ether Mail",
                                  version="1",
                                  chainId=1,
                                  verifyingContract="0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC")

        private_key = keccak_256("cow".encode('utf-8'))
        self.account_for_structured: LocalAccount = Account.from_key(private_key)
        self.signer_structured = PrivateKeyEthSigner(self.account_for_structured, 1)

        self.person_from = Person(name="Cow", wallet="0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826")
        self.person_to = Person(name="Bob", wallet="0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB")
        self.mail = make_mail(from_=self.person_from, to=self.person_to, content="Hello, Bob!")

    def test_get_domain(self):
        domain = self.signer.get_domain()
        values = domain.values
        self.assertEqual(values["name"], 'zkSync')
        self.assertEqual(values["version"], '2')
        self.assertEqual(values["chainId"], 5)

    def test_sign_message(self):
        message = "test message for signing"
        signature = self.signer.sign_message(message)
        result = self.signer.verify_signature(signature, message)
        self.assertTrue(result)

    def test_sing_typed_data(self):
        ret = self.signer_structured.sign_typed_data(self.mail, self.domain)
        self.assertEqual(self._TEST_TYPED_EXPECTED_SIGNATURE, ret)

    def test_verify_signed_typed_data(self):
        ret = self.signer_structured.verify_typed_data(self._TEST_TYPED_EXPECTED_SIGNATURE, self.mail, self.domain)
        self.assertTrue(ret)
