import json
from unittest import TestCase
from eth_utils.crypto import keccak_256
from eip712_structs import EIP712Struct, String, Address, make_domain
from zksync2.signer.eth_account_patch.encode_structed_data import encode_structured_data
from zksync2.core.utils import pad_front_bytes


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


class TestEIP712Structured(TestCase):

    def setUp(self) -> None:
        self.person_from = Person(name="Cow", wallet="0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826")
        self.person_to = Person(name="Bob", wallet="0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB")
        self.mail = make_mail(from_=self.person_from, to=self.person_to, content="Hello, Bob!")
        self.domain = make_domain(name="Ether Mail",
                                  version="1",
                                  chainId=1,
                                  verifyingContract="0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC")

    def test_encode_type(self):
        result = self.mail.encode_type()
        self.assertEqual('Mail(Person from,Person to,string contents)Person(string name,address wallet)', result)

    def test_hash_encoded_type(self):
        result = self.mail.type_hash()
        self.assertEqual('a0cedeb2dc280ba39b857546d74f5549c3a1d7bdc2dd96bf881f76108e23dac2', result.hex())

    def test_encode_person(self):
        from_str = self.mail.get_data_value('from').to_message_json(self.domain)
        value = json.loads(from_str)
        ret = encode_structured_data(value)
        self.assertEqual('fc71e5fa27ff56c350aa531bc129ebdf613b772b6604664f5d8dbe21b85eb0c8', ret.body.hex())

        to_str = self.mail.get_data_value('to').to_message_json(self.domain)
        value = json.loads(to_str)
        ret = encode_structured_data(value)
        self.assertEqual('cd54f074a4af31b4411ff6a60c9719dbd559c221c8ac3492d9d872b041d703d1', ret.body.hex())

    def test_encode_mail_data(self):
        struct_message_json = self.mail.to_message_json(self.domain)
        value = json.loads(struct_message_json)
        ret = encode_structured_data(value)
        self.assertEqual('c52c0ee5d84264471806290a3f2c4cecfc5490626bf912d01f240d7a274b371e', ret.body.hex())

    def test_singed_bytes(self):
        result_bytes = self.mail.signable_bytes(self.domain)
        ret = keccak_256(result_bytes)
        self.assertEqual('be609aee343fb3c4b28e1df9e632fca64fcfaede20f02e86244efddf30957bd2', ret.hex())

    def test_encode_content(self):
        val = self.mail.get_data_value('contents')
        ret = keccak_256(val.encode())
        self.assertEqual('b5aadf3154a261abdd9086fc627b61efca26ae5702701d05cd2305f7c52a2fc8', ret.hex())

    def test_encode_domain(self):
        type_hash = self.domain.type_hash()
        ret = self.domain.encode_value()
        ret = type_hash + ret
        ret = keccak_256(ret)
        self.assertEqual('f2cee375fa42b42143804025fc449deafd50cc031ca257e0b194a650a912090f', ret.hex())

    def test_encode_domain_members(self):
        name = self.domain.get_data_value('name')
        name_hash = keccak_256(name.encode())
        self.assertEqual('c70ef06638535b4881fafcac8287e210e3769ff1a8e91f1b95d6246e61e4d3c6', name_hash.hex())

        version = self.domain.get_data_value('version')
        version_hash = keccak_256(version.encode())
        self.assertEqual('c89efdaa54c0f20c7adf612882df0950f5a951637e0307cdcb4c672f298b8bc6', version_hash.hex())

        chain_id = self.domain.get_data_value('chainId')
        chain_id_padded = pad_front_bytes(chain_id.to_bytes(2, 'big'), 32)
        self.assertEqual('0000000000000000000000000000000000000000000000000000000000000001', chain_id_padded.hex())

        verified_contract = self.domain.get_data_value('verifyingContract')
        verified_contract = verified_contract[2:]
        verified_contract_hash = b'\0'*12 + bytes.fromhex(verified_contract)

        self.assertEqual("000000000000000000000000cccccccccccccccccccccccccccccccccccccccc",
                         verified_contract_hash.hex())
