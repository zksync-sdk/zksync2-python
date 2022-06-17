import rlp
from rlp.sedes import big_endian_int, binary
from rlp.sedes import List as rlpList
from transaction.transaction import TransactionBase, TransactionType


class Transaction712:
    EIP_712_TX_TYPE = b'\x70'
    _DEFAULT_ADDRESS_STR = "0" * 40

    def __init__(self, transaction: TransactionBase, chain_id):
        self.transaction = transaction
        self.chain_id = chain_id

    def as_rlp_values(self, signature=None):
        transaction_request = self.transaction.transaction_request()
        # if (signatureData != null) {
        #     byte[] v = signatureData.getV()[0] == (byte) 0 ? new byte[] {}: signatureData.getV();
        #     result.add(RlpString.create(v)); //
        #         6
        #     result.add(RlpString.create(Bytes.trimLeadingZeroes(signatureData.getR()))); // 7
        #     result.add(RlpString.create(Bytes.trimLeadingZeroes(signatureData.getS()))); // 8
        # }

        maybe_empty_lst = []
        if self.transaction.get_type() == TransactionType.DEPLOY:
            maybe_empty_lst = self.transaction.factory_deps

        vals = transaction_request.values
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
                    ('factoryDeps', rlpList)
                ]

            v_bytes = bytes()
            # TODO: getV[0] is big endian or little , and what is the bytes amount??
            if signature.v == 0:
                v_bytes = bytes(signature.v)
            value = InternalRepresentation(nonce=transaction_request.nonce.none_val,
                                           gasPrice=transaction_request.gasPrice.none_val,
                                           gasLimit=transaction_request.gasPrice.none_val,
                                           to=transaction_request.to.none_val,
                                           value=transaction_request.value.none_val,
                                           data=transaction_request.data.none_val,
                                           v=v_bytes,
                                           r=bytes(signature.r),  # TODO: must be lstrip(trim leading by default)
                                           s=bytes(signature.s),  # TODO: must be lstrip(trim leading by default)
                                           chain_id=self.chain_id,
                                           feeToken=transaction_request.feeToken.none_val,
                                           withdrawToken=transaction_request.withdrawToken.none_val,
                                           ergsPerStorage=transaction_request.ergsPerStorage.none_val,
                                           ergsPerPubdata=transaction_request.ergsPerPubdata.none_val,
                                           factoryDeps=[maybe_empty_lst]
                                           )
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
                    ('factoryDeps', rlpList(strict=False))
                ]
            address = vals['to']
            if address.startswith("0x"):
                address = address[2:]
            value = InternalRepresentation(nonce=vals['nonce'],
                                           gasPrice=vals['gasPrice'],
                                           gasLimit=vals['gasLimit'],
                                           to=bytes.fromhex(address),
                                           value=vals['value'],
                                           data=vals['data'],
                                           chain_id=self.chain_id,
                                           feeToken=bytes.fromhex(vals['feeToken'][2:]),
                                           withdrawToken=bytes.fromhex(vals['withdrawToken'][2:]),
                                           ergsPerStorage=vals['ergsPerStorage'],
                                           ergsPerPubdata=vals['ergsPerPubdata'],
                                           factoryDeps=[maybe_empty_lst]
                                           )
            result = rlp.encode(value, infer_serializer=True, cache=False)
        return result
