# from zk_types import Dict
from abc import ABC, abstractmethod
from typing import Union, Optional
from web3 import Web3, HTTPProvider
from web3.types import RPCEndpoint, RPCResponse
from web3._utils.module import attach_modules
from web3.eth import Eth
from zk_types.zk_types import *
from eth_typing import Address, BlockIdentifier, HexAddress, URI
from web3.module import Module
from web3.method import Method, default_root_munger
from typing import (
    Any,
    Awaitable,
    Callable,
    List,
    NoReturn,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
    overload,
)


# # INFO: can be private class
# # CAN BE A MODULE
# class ZkSyncBase(Eth, ABC):
#
#     @abstractmethod
#     def zks_estimate_fee(self, transaction: Transaction) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def zks_main_contract(self) -> RPCResponse:
#         raise NotImplemented
#
#     # INFO: might need hexBytes
#     @abstractmethod
#     def zks_get_l1_withdraw_tx(self, transaction_hash: L1WithdrawHash) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def zks_get_account_transactions(self, address: Address, before: Before, limit: Limit) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def zks_get_confirmed_tokens(self, offset: Before, limit: Limit) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def zks_is_token_liquid(self, token_address: TokenAddress) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def zks_get_token_price(self, token_address: TokenAddress) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def zks_l1_chain_id(self) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def eth_get_balance(self, address: Address,
#                         default_block_param: BlockIdentifier, token_address: TokenAddress) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def zks_set_contract_debug_info(self, contract_address: HexAddress,
#                                     contract_debug_info: ContractDebugInfo) -> RPCResponse:
#         raise NotImplemented
#
#     @abstractmethod
#     def zks_get_contract_debug_info(self, contract_address: str) -> RPCResponse:
#         raise NotImplemented
#
#     # INFO: might need hexBytes
#     @abstractmethod
#     def zks_get_transaction_trace(self, transaction_hash: str) -> RPCResponse:
#         raise NotImplemented
#
#     # INFO: might need hexBytes
#     @abstractmethod
#     def zks_get_all_account_balances(self, address: str) -> RPCResponse:
#         raise NotImplemented


# class ZkSyncJsonRPC(ZkSyncBase, HTTPProvider, ABC):
# class ZkSyncProvider(HTTPProvider):
#     zk_estimate_fee_rpc = RPCEndpoint("zks_estimateFee")
#     zk_main_contract_rpc = RPCEndpoint("zks_main_contract")
#     zks_get_l1_withdraw_tx_rpc = RPCEndpoint("zks_get_l1_withdraw_tx")
#     zks_get_account_transactions_rpc = RPCEndpoint("zks_get_account_transactions")
#     zks_get_confirmed_tokens_rpc = RPCEndpoint("zks_get_confirmed_tokens")
#     zks_is_token_liquid_rpc = RPCEndpoint("zks_is_token_liquid")
#     zks_get_token_price_rpc = RPCEndpoint("zks_get_token_price")
#     zks_l1_chain_id_rpc = RPCEndpoint("zks_l1_chain_id")
#     eth_get_balance_rpc = RPCEndpoint("eth_get_balance")
#     zks_set_contract_debug_info_rpc = RPCEndpoint("zks_set_contract_debug_info")
#     zks_get_contract_debug_info_rpc = RPCEndpoint("zks_get_contract_debug_info")
#     zks_get_transaction_trace_rpc = RPCEndpoint("zks_get_transaction_trace")
#     zks_get_all_account_balances_rpc = RPCEndpoint("zks_get_all_account_balances")
#
#     # def __init__(self, web3: Web3, url: Optional[Union[URI, str]]):
#     def __init__(self, url: Optional[Union[URI, str]]):
#         # ZkSyncBase.__init__(self, web3)
#         HTTPProvider.__init__(self, url)
#
#     def zks_estimate_fee(self, transaction: Transaction):
#         return self.make_request(self.zk_estimate_fee_rpc, transaction)
#
#     def zks_main_contract(self):
#         return self.make_request(self.zk_main_contract_rpc, None)
#
#     # INFO: might need hexBytes
#     def zks_get_l1_withdraw_tx(self, transaction_hash: L1WithdrawHash):
#         return self.make_request(self.zks_get_l1_withdraw_tx_rpc, [transaction_hash])
#
#     def zks_get_account_transactions(self, address: Address, before: Before, limit: Limit):
#         return self.make_request(self.zks_get_account_transactions_rpc, [address, before, limit])
#
#     def zks_get_confirmed_tokens(self, offset: Before, limit: Limit):
#         return self.make_request(self.zks_get_confirmed_tokens_rpc, [offset, limit])
#
#     def zks_is_token_liquid(self, token_address: TokenAddress):
#         return self.make_request(self.zks_is_token_liquid_rpc, [token_address])
#
#     def zks_get_token_price(self, token_address: TokenAddress):
#         return self.make_request(self.zks_get_token_price_rpc, [token_address])
#
#     def zks_l1_chain_id(self):
#         return self.make_request(self.zks_l1_chain_id_rpc, None)
#
#     def eth_get_balance(self, address: Address, default_block_param: BlockIdentifier, token_address: TokenAddress):
#         """ INFO: needs to check default_block_param type"""
#         return self.make_request(self.eth_get_balance_rpc, [address, default_block_param, token_address])
#
#     def zks_set_contract_debug_info(self, contract_address: HexAddress, contract_debug_info: ContractDebugInfo):
#         return self.make_request(self.zks_set_contract_debug_info_rpc, [contract_address, contract_debug_info])
#
#     def zks_get_contract_debug_info(self, contract_address: HexAddress):
#         return self.make_request(self.zks_get_contract_debug_info_rpc, [contract_address])
#
#     # INFO: might need hexBytes
#     def zks_get_transaction_trace(self, transaction_hash: Hash32):
#         return self.make_request(self.zks_get_transaction_trace_rpc, [transaction_hash])
#
#     # INFO: might need hexBytes
#     def zks_get_all_account_balances(self, address: Address):
#         return self.make_request(self.zks_get_all_account_balances_rpc, [address])

# class ZkSyncBuilder:
#     @classmethod
#     def build(cls, web3_module: Web3, url: Optional[Union[URI, str]]):
#         zksync_provider = ZkSyncProvider(url)
#         attach_modules(web3_module, {"zksync": (zksync_provider,)})
#         return web3_module

#     zk_estimate_fee_rpc = RPCEndpoint("zks_estimateFee")
#     zk_main_contract_rpc = RPCEndpoint("zks_main_contract")
#     zks_get_l1_withdraw_tx_rpc = RPCEndpoint("zks_get_l1_withdraw_tx")
#     zks_get_account_transactions_rpc = RPCEndpoint("zks_get_account_transactions")
#     zks_get_confirmed_tokens_rpc = RPCEndpoint("zks_get_confirmed_tokens")
#     zks_is_token_liquid_rpc = RPCEndpoint("zks_is_token_liquid")
#     zks_get_token_price_rpc = RPCEndpoint("zks_get_token_price")
#     zks_l1_chain_id_rpc = RPCEndpoint("zks_l1_chain_id")
#     eth_get_balance_rpc = RPCEndpoint("eth_get_balance")
#     zks_get_all_account_balances_rpc = RPCEndpoint("zks_get_all_account_balances")

# MAKE IT LATER !!! :)))))
#     zks_set_contract_debug_info_rpc = RPCEndpoint("zks_set_contract_debug_info")
#     zks_get_contract_debug_info_rpc = RPCEndpoint("zks_get_contract_debug_info")
#     zks_get_transaction_trace_rpc = RPCEndpoint("zks_get_transaction_trace")


# def _get_account_transaction_munger(module, val: Tuple[Address, Before, Limit]) -> Dict[int, Any]:
#     ret = {
#         0: val[0],
#         1: val[1],
#         2: val[2]
#     }
#     return ret


class ZkSync(Module):
    zks_main_contract_rpc = RPCEndpoint("zks_getMainContract")
    zks_estimate_fee_rpc = RPCEndpoint("zks_estimateFee")
    zks_get_l1_withdraw_tx_rpc = RPCEndpoint("zks_getL1WithdrawalTx")
    zks_get_account_transactions_rpc = RPCEndpoint("zks_getAccountTransactions")
    zks_get_confirmed_tokens_rpc = RPCEndpoint("zks_getConfirmedTokens")
    zks_is_token_liquid_rpc = RPCEndpoint("zks_isTokenLiquid")
    zks_get_token_price_prc = RPCEndpoint("zks_getTokenPrice")
    zks_l1_chain_id_rpc = RPCEndpoint("zks_L1ChainId")
    zks_set_contract_debug_info_rpc = RPCEndpoint("zks_setContractDebugInfo")

    _zks_main_contract: Method[Callable[[], HexStr]] = Method(
        zks_main_contract_rpc,
        mungers=None
    )

    _zks_estimate_fee: Method[Callable[[Transaction], EstimateFeeResult]] = Method(
        zks_estimate_fee_rpc,
        mungers=[default_root_munger]
    )

    _zks_get_l1_withdraw_tx: Method[Callable[[L1WithdrawHash], TransactionHash]] = Method(
        zks_get_l1_withdraw_tx_rpc,
        mungers=[default_root_munger]
    )

    _zks_get_account_transactions: Method[Callable[[Address, Before, Limit], List[TransactionInfo]]] = Method(
        zks_get_account_transactions_rpc,
        mungers=[default_root_munger]
    )

    _zks_get_confirmed_tokens: Method[Callable[[Before, Limit], List[TokenDescription]]] = Method(
        zks_get_confirmed_tokens_rpc,
        mungers=[default_root_munger]
    )

    _zks_is_token_liquid: Method[Callable[[TokenAddress], bool]] = Method(
        zks_is_token_liquid_rpc,
        mungers=[default_root_munger]
    )

    _zks_get_token_price: Method[Callable[[TokenAddress], TokenPriceUSD]] = Method(
        zks_get_token_price_prc,
        mungers=[default_root_munger]
    )

    _zks_l1_chain_id: Method[Callable[[], HexBytes]] = Method(
        zks_l1_chain_id_rpc,
        mungers=None
    )

    _zks_set_contract_debug_info: Method[Callable[[HexAddress, ContractDebugInfo], Any]] = Method(
        zks_set_contract_debug_info_rpc,
        mungers=[default_root_munger]
    )

    def __init__(self, web3: "Web3"):
        super(ZkSync, self).__init__(web3)

    # @property
    def zks_main_contract(self) -> HexStr:
        return self._zks_main_contract()

    def zks_estimate_fee(self, transaction: Transaction) -> EstimateFeeResult:
        return self._zks_estimate_fee(transaction)

    def zks_get_l1_withdraw_tx(self, withdraw_hash: L1WithdrawHash) -> TransactionHash:
        return self._zks_get_l1_withdraw_tx(withdraw_hash)

    def zks_get_account_transactions(self, address: Address, before: Before, limit: Limit) -> List[TransactionInfo]:
        return self._zks_get_account_transactions(address, before, limit)

    def zks_get_confirmed_tokens(self, offset: Before, limit: Limit) -> List[TokenDescription]:
        return self._zks_get_confirmed_tokens(offset, limit)

    def zks_is_token_liquid(self, token_address: TokenAddress) -> bool:
        return self._zks_is_token_liquid(token_address)

    def zks_get_token_price(self, token_address: TokenAddress) -> TokenPriceUSD:
        return self._zks_get_token_price(token_address)

    def zks_l1_chain_id(self) -> HexBytes:
        return self._zks_l1_chain_id()

    # TODO: CHECK IT
    def zks_set_contract_debug_info(self, contract_address: ContractAddress, debug_info: ContractDebugInfo) -> Any:
        return self._zks_set_contract_debug_info([contract_address, debug_info])
