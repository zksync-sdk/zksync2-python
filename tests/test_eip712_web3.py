from unittest import TestCase
from eth_account.messages import encode_structured_data


class TestEIP712BuiltIn(TestCase):

    def setUp(self) -> None:
        self.msg = {
            'domain': {
                'chainId': 1,
                'name': 'Ether Mail',
                'version': '1',
                'verifyingContract': '0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC'
            },
            'message': {
                'contents': 'Hello, Bob!',
                'from': {
                    'name': 'Cow',
                    'wallet': "0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826",
                },
                'to': {
                    'name': 'Bob',
                    'wallet': '0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB',
                },
            },
            'primaryType': 'Mail',
            'types': {
                'EIP712Domain': [
                    {'name': 'name', 'type': 'string'},
                    {'name': 'version', 'type': 'string'},
                    {'name': 'chainId', 'type': 'uint256'},
                    {'name': 'verifyingContract', 'type': 'address'},
                ],
                'Person': [
                    {'name': 'name', 'type': 'string'},
                    {'name': 'wallet', 'type': 'address'},
                ],
                'Mail': [
                    {'name': 'from', 'type': 'Person'},
                    {'name': 'to', 'type': 'Person'},
                    {'name': 'contents', 'type': 'string'},
                ]
            }
        }

    @staticmethod
    def build_person(name, wallet):
        return {
            'domain': {
                'chainId': 1,
                'name': 'Ether Mail',
                'version': '1',
                'verifyingContract': '0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC'
            },
            'message': {
                'name': name,
                'wallet': wallet
            },
            'primaryType': 'Person',
            'types': {
                'EIP712Domain': [
                    {'name': 'name', 'type': 'string'},
                    {'name': 'version', 'type': 'string'},
                    {'name': 'chainId', 'type': 'uint256'},
                    {'name': 'verifyingContract', 'type': 'address'},
                ],
                'Person': [
                    {'name': 'name', 'type': 'string'},
                    {'name': 'wallet', 'type': 'address'},
                ],
            }
        }

    @staticmethod
    def build_content(content):
        return {
            'domain': {
                'chainId': 1,
                'name': 'Ether Mail',
                'version': '1',
                'verifyingContract': '0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC'
            },
            'message': {
                'contents': content
            },
            'primaryType': 'contents',
            'types': {
                'EIP712Domain': [
                    {'name': 'name', 'type': 'string'},
                    {'name': 'version', 'type': 'string'},
                    {'name': 'chainId', 'type': 'uint256'},
                    {'name': 'verifyingContract', 'type': 'address'},
                ],
                'contents':  [
                    {'name': 'contents', 'type': 'string'}
                ]
            }
        }

    def test_encode_mail_data(self):
        """
        # @Test
        # public void testEncodeMailData() {
        #     final byte[] data = Eip712Encoder.encodeValue(this.message.intoEip712Struct()).getValue();
        #
        #     assertEquals("0xc52c0ee5d84264471806290a3f2c4cecfc5490626bf912d01f240d7a274b371e", Numeric.toHexString(data));
        # }
        """

        ret = encode_structured_data(self.msg)
        self.assertEqual("c52c0ee5d84264471806290a3f2c4cecfc5490626bf912d01f240d7a274b371e", ret.body.hex())

    def test_encode_person_data(self):
        """
        # @Test
        # public void testEncodePersonData() {
        #     final byte[] fromHash = Eip712Encoder.encodeValue(this.message.from.intoEip712Struct()).getValue();
        #     final byte[] toHash = Eip712Encoder.encodeValue(this.message.to.intoEip712Struct()).getValue();
        #
        #     assertEquals("0xfc71e5fa27ff56c350aa531bc129ebdf613b772b6604664f5d8dbe21b85eb0c8", Numeric.toHexString(fromHash));
        #     assertEquals("0xcd54f074a4af31b4411ff6a60c9719dbd559c221c8ac3492d9d872b041d703d1", Numeric.toHexString(toHash));
        # }
        """
        person_from = self.build_person('Cow', '0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826')
        ret = encode_structured_data(person_from)
        self.assertEqual(ret.body.hex(), "fc71e5fa27ff56c350aa531bc129ebdf613b772b6604664f5d8dbe21b85eb0c8")

        person_to = self.build_person('Bob', '0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB')
        ret = encode_structured_data(person_to)
        self.assertEqual(ret.body.hex(), "cd54f074a4af31b4411ff6a60c9719dbd559c221c8ac3492d9d872b041d703d1")

    def test_encode_content_value(self):
        """
        TODO: figure out how to encode separated field
        """
        # content = self.build_content("Hello, Bob!")
        ret = encode_structured_data(text='Hello, Bob!')
        self.assertEqual(ret.body.hex(), 'b5aadf3154a261abdd9086fc627b61efca26ae5702701d05cd2305f7c52a2fc8')
