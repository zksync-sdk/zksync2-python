from collections.abc import Mapping
from typing import Union
from eth_account.messages import SignableMessage
from eth_utils.curried import to_text
from hexbytes import HexBytes

from eth_account._utils.structured_data.hashing import (
    hash_domain,
    hash_message as hash_eip712_message,
    load_and_validate_structured_message,
)

from zksync2.signer.eth_account_patch.validation import validate_structured_data


def encode_structured_data(
        primitive: Union[bytes, int, Mapping] = None,
        *,
        hexstr: str = None,
        text: str = None) -> SignableMessage:
    """
    Encode an EIP-712_ message.

    EIP-712 is the "structured data" approach (ie~ version 1 of an EIP-191 message).

    Supply the message as exactly one of the three arguments:

        - primitive, as a dict that defines the structured data
        - primitive, as bytes
        - text, as a json-encoded string
        - hexstr, as a hex-encoded (json-encoded) string

    .. WARNING:: Note that this code has not gone through an external audit, and
        the test cases are incomplete.
        Also, watch for updates to the format, as the EIP is still in DRAFT.

    :param primitive: the binary message to be signed
    :type primitive: bytes or int or Mapping (eg~ dict )
    :param hexstr: the message encoded as hex
    :param text: the message as a series of unicode characters (a normal Py3 str)
    :returns: The EIP-191 encoded message, ready for signing

    .. _EIP-712: https://eips.ethereum.org/EIPS/eip-712
    """
    if isinstance(primitive, Mapping):
        validate_structured_data(primitive)
        structured_data = primitive
    else:
        message_string = to_text(primitive, hexstr=hexstr, text=text)
        structured_data = load_and_validate_structured_message(message_string)
    return SignableMessage(
        HexBytes(b'\x01'),
        hash_domain(structured_data),
        hash_eip712_message(structured_data),
    )
