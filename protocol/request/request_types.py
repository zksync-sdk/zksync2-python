from abc import ABC, abstractmethod
from dataclasses import dataclass, astuple, asdict
from typing import TypedDict, List, Optional, Dict
from eth_typing import HexStr
from web3.types import AccessList
from protocol.core.types import PaymasterParams


@dataclass
class EIP712Meta(dict):
    ERGS_PER_PUB_DATA_DEFAULT = 160000

    ergs_per_pub_data: int = ERGS_PER_PUB_DATA_DEFAULT
    custom_signature: Optional[bytes] = None
    factory_deps: Optional[List[bytes]] = None
    paymaster_params: Optional[PaymasterParams] = None

    def _as_dict(self) -> dict:
        ret = {
            "ergsPerPubdata": self.ergs_per_pub_data
        }
        if self.custom_signature is not None:
            ret["customSignature"] = self.custom_signature

        if self.factory_deps is not None:
            ret["factoryDeps"] = self.factory_deps
        # if self.paymaster_params is not None:
        #     ret["paymasterParams"] = self.paymaster_params.as_dict()
        return ret

    def __iter__(self):
        yield astuple(self)

    def items(self):
        # return asdict(self).items()
        return self._as_dict().items()


Transaction = TypedDict(
    "Transaction",
    {
        "from": HexStr,
        "to": HexStr,
        "gas": int,
        "gasPrice": int,
        "value": int,
        "data": HexStr,
        "transactionType": int,
        "accessList": Optional[AccessList],
        "eip712Meta": EIP712Meta,
    }, total=False)


class FunctionCallTxBuilderBase(ABC):

    @abstractmethod
    def build(self) -> Transaction:
        raise NotImplementedError


class FunctionCallTxBuilder(FunctionCallTxBuilderBase, ABC):

    def __init__(self,
                 from_: HexStr,
                 to: HexStr,
                 ergs_price: int,
                 ergs_limit: int,
                 data: HexStr,
                 value: int = 0):
        eip712_meta_default = EIP712Meta()
        self.tx: Transaction = {
            "from": from_,
            "to": to,
            "gas": ergs_limit,
            "gasPrice": ergs_price,
            "value": value,
            "data": data,
            "transactionType": 113,
            # "eip712Meta":  eip712_meta_default.as_dict()
            "eip712Meta": eip712_meta_default
        }

    def build(self) -> Transaction:
        return self.tx


# class FunctionCallTxWithValue(FunctionCallTxBuilderBase, ABC):
#
#     def __int__(self,
#                 from_: HexStr,
#                 to: HexStr,
#                 ergs_price: int,
#                 ergs_limit: int,
#                 value: int,
#                 data: HexStr):
#         eip_meta_default = EIP712Meta()
#
#         self.tx: Transaction = {
#             "from": from_,
#             "to": to,
#             "gas": ergs_limit,
#             "gasPrice": ergs_price,
#             "value": value,
#             "data": data,
#             "transactionType": 113,
#             # "eip712Meta": eip_meta_default.as_dict()
#             "eip712Meta": eip_meta_default
#         }
#
#     def build(self) -> Transaction:
#         return self.tx
