from unittest import TestCase
from crypto.eth_signer import PrivateKeyEthSigner
from eth_account.signers.local import LocalAccount
from eth_account import Account
from hexbytes import HexBytes


def random_key_generator(s: int):
    """
    INFO: Use it for test key generation
    """
    import random
    import string
    char_set = string.hexdigits + string.digits
    return ''.join(random.sample(char_set * s, s))


class TestEthSigner(TestCase):
    _TEST_PRIVATE_KEY = "0x119dB1AfDBB7Be947Cfb340035e306b64E982E0C5eC63045786c9C7AfB56d560"

    def setUp(self) -> None:
        account: LocalAccount = Account.from_key(self._TEST_PRIVATE_KEY)
        self.signer = PrivateKeyEthSigner(account, HexBytes(5))

    def test_get_domain(self):
        domain = self.signer.get_domain()
        self.assertEqual(domain.name, 'zkSync')
        self.assertEqual(domain.version, '2')
        self.assertEqual(domain.chainId, HexBytes(5))

    def test_sign_message(self):
        message = "test message for signing"
        signature = self.signer.sign_message(message)
        result = self.signer.verify_signature(signature, message)
        self.assertTrue(result, True)
