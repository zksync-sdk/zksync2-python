import rlp
from rlp.sedes import big_endian_int, binary
from rlp.sedes import List as rlpList
from transaction.transaction import TransactionBase, TransactionType


class Transaction712:
    EIP_712_TX_TYPE = b'\x70'

    def __init__(self, transaction: TransactionBase, chain_id):
        self.transaction = transaction
        self.chain_id = chain_id

    def _get_withdraw_token(self, value: str) -> bytes:
        if self.transaction.get_type() == TransactionType.WITHDRAW:
            return bytes.fromhex(value)
        else:
            # INFO: must be empty byte array
            return bytes()

    def as_rlp_values(self, signature=None):
        transaction_request = self.transaction.transaction_request()
        maybe_empty_lst = []
        elements_to_process = None
        if self.transaction.get_type() == TransactionType.DEPLOY:
            maybe_empty_lst = self.transaction.factory_deps
            elements_to_process = [binary for _ in range(len(maybe_empty_lst))]

        vals = transaction_request.values

        for entry in ['to', 'feeToken', 'withdrawToken']:
            address_like = vals[entry]
            if address_like.startswith("0x"):
                vals[entry] = address_like[2:]

        withdraw_token = self._get_withdraw_token(vals['withdrawToken'])

        if signature is not None:
            class InternalRepresentation(rlp.Serializable):
                fields = [
                    ('nonce', big_endian_int),
                    ('gasPrice', big_endian_int),
                    ('gasLimit', big_endian_int),
                    ('to', binary),  # addresses that start with zeros should be encoded with the zeros included,
                    # not as numeric values, TODO: for null values needs to be text ???
                    ('value', big_endian_int),
                    ('data', binary),
                    ('v', binary),
                    ('r', binary),
                    ('s', binary),
                    ('chain_id', big_endian_int),
                    ('feeToken', binary),
                    ('withdrawToken', binary),
                    ('ergsPerStorage', big_endian_int),
                    ('ergsPerPubdata', big_endian_int),
                    ('factoryDeps', rlpList(elements=elements_to_process, strict=False))
                ]

            v_bytes = bytes()
            # TODO: getV[0] is big endian or little , and what is the bytes amount??
            if signature.v == 0:
                v_bytes = bytes(signature.v)

            value = InternalRepresentation(
                nonce=vals['nonce'],
                gasPrice=vals['gasPrice'],
                gasLimit=vals['gasLimit'],
                to=bytes.fromhex(vals['to']),
                value=vals['value'],
                data=vals['data'],
                v=v_bytes,
                r=bytes(signature.r),  # TODO: must be lstrip(trim leading by default)
                s=bytes(signature.s),  # TODO: must be lstrip(trim leading by default)
                chain_id=self.chain_id,
                feeToken=bytes.fromhex(vals['feeToken']),
                withdrawToken=withdraw_token,
                ergsPerStorage=vals['ergsPerStorage'],
                ergsPerPubdata=vals['ergsPerPubdata'],
                factoryDeps=[maybe_empty_lst])
            result = rlp.encode(value, infer_serializer=False, cache=False)
        else:
            class InternalRepresentation(rlp.Serializable):
                fields = [
                    ('nonce', big_endian_int),
                    ('gasPrice', big_endian_int),
                    ('gasLimit', big_endian_int),
                    ('to', binary),  # addresses that start with zeros should be encoded with the zeros included,
                    # not as numeric values, TODO: for null values needs to be text ???
                    ('value', big_endian_int),
                    ('data', binary),
                    ('chain_id', big_endian_int),
                    ('feeToken', binary),
                    ('withdrawToken', binary),
                    ('ergsPerStorage', big_endian_int),
                    ('ergsPerPubdata', big_endian_int),
                    ('factoryDeps', rlpList(elements=elements_to_process, strict=False))
                ]

            value = InternalRepresentation(
                nonce=vals['nonce'],
                gasPrice=vals['gasPrice'],
                gasLimit=vals['gasLimit'],
                to=bytes.fromhex(vals['to']),
                value=vals['value'],
                data=vals['data'],
                chain_id=self.chain_id,
                feeToken=bytes.fromhex(vals['feeToken']),
                withdrawToken=withdraw_token,
                ergsPerStorage=vals['ergsPerStorage'],
                ergsPerPubdata=vals['ergsPerPubdata'],
                # TODO: CHECK TYPE MUST BE List of Bytes
                factoryDeps=maybe_empty_lst
            )
            result = rlp.encode(value, infer_serializer=True, cache=False)
        return result
