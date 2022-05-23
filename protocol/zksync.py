# from types import Dict
from abc import ABC, abstractmethod
# from typing import Union, Optional

import web3
from web3 import Web3
from web3.types import RPCEndpoint,  RPCResponse
from web3._utils.module import attach_modules
from web3.eth import Eth
# from methods.transaction import Transaction
from types.types import *
from eth_typing import Address, BlockIdentifier, HexAddress


# INFO: can be private class
class ZkSyncBase(Eth, ABC):

    @abstractmethod
    def zks_estimate_fee(self, transaction: Transaction) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def zks_main_contract(self) -> RPCResponse:
        raise NotImplemented

    # INFO: might need hexBytes
    @abstractmethod
    def zks_get_l1_withdraw_tx(self, transaction_hash: L1WithdrawHash) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def zks_get_account_transactions(self, address: Address, before: Before, limit: Limit) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def zks_get_confirmed_tokens(self, offset: Before, limit: Limit) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def zks_is_token_liquid(self, token_address: TokenAddress) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def zks_get_token_price(self, token_address: TokenAddress) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def zks_l1_chain_id(self) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def eth_get_balance(self, address: Address,
                        default_block_param: BlockIdentifier, token_address: TokenAddress) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def zks_set_contract_debug_info(self, contract_address: HexAddress,
                                    contract_debug_info: ContractDebugInfo) -> RPCResponse:
        raise NotImplemented

    @abstractmethod
    def zks_get_contract_debug_info(self, contract_address: str) -> RPCResponse:
        raise NotImplemented

    # INFO: might need hexBytes
    @abstractmethod
    def zks_get_transaction_trace(self, transaction_hash: str) -> RPCResponse:
        raise NotImplemented

    # INFO: might need hexBytes
    @abstractmethod
    def zks_get_all_account_balances(self, address: str) -> RPCResponse:
        raise NotImplemented


class ZkSyncJsonRPC(ZkSyncBase, web3.HTTPProvider, ABC):
    zk_estimate_fee_rpc = RPCEndpoint("zks_estimateFee")
    zk_main_contract_rpc = RPCEndpoint("zks_main_contract")
    zks_get_l1_withdraw_tx_rpc = RPCEndpoint("zks_get_l1_withdraw_tx")
    zks_get_account_transactions_rpc = RPCEndpoint("zks_get_account_transactions")
    zks_get_confirmed_tokens_rpc = RPCEndpoint("zks_get_confirmed_tokens")
    zks_is_token_liquid_rpc = RPCEndpoint("zks_is_token_liquid")
    zks_get_token_price_rpc = RPCEndpoint("zks_get_token_price")
    zks_l1_chain_id_rpc = RPCEndpoint("zks_l1_chain_id")
    eth_get_balance_rpc = RPCEndpoint("eth_get_balance")
    zks_set_contract_debug_info_rpc = RPCEndpoint("zks_set_contract_debug_info")
    zks_get_contract_debug_info_rpc = RPCEndpoint("zks_get_contract_debug_info")
    zks_get_transaction_trace_rpc = RPCEndpoint("zks_get_transaction_trace")
    zks_get_all_account_balances_rpc = RPCEndpoint("zks_get_all_account_balances")

    @abstractmethod
    def zks_estimate_fee(self, transaction: Transaction):
        return self.make_request(self.zk_estimate_fee_rpc, transaction)

    @abstractmethod
    def zks_main_contract(self):
        return self.make_request(self.zk_main_contract_rpc, None)

    # INFO: might need hexBytes
    @abstractmethod
    def zks_get_l1_withdraw_tx(self, transaction_hash: L1WithdrawHash):
        return self.make_request(self.zks_get_l1_withdraw_tx_rpc, [transaction_hash])

    @abstractmethod
    def zks_get_account_transactions(self, address: Address, before: Before, limit: Limit):
        return self.make_request(self.zks_get_account_transactions_rpc, [address, before, limit])

    @abstractmethod
    def zks_get_confirmed_tokens(self, offset: Before, limit: Limit):
        return self.make_request(self.zks_get_confirmed_tokens_rpc, [offset, limit])

    @abstractmethod
    def zks_is_token_liquid(self, token_address: TokenAddress):
        return self.make_request(self.zks_is_token_liquid_rpc, [token_address])

    @abstractmethod
    def zks_get_token_price(self, token_address: TokenAddress):
        return self.make_request(self.zks_get_token_price_rpc, [token_address])

    @abstractmethod
    def zks_l1_chain_id(self):
        return self.make_request(self.zks_l1_chain_id_rpc, None)

    @abstractmethod
    def eth_get_balance(self, address: Address, default_block_param: BlockIdentifier, token_address: TokenAddress):
        """ INFO: needs to check default_block_param type"""
        return self.make_request(self.eth_get_balance_rpc, [address, default_block_param, token_address])

    @abstractmethod
    def zks_set_contract_debug_info(self, contract_address: HexAddress, contract_debug_info: ContractDebugInfo):
        return self.make_request(self.zks_set_contract_debug_info_rpc, [contract_address, contract_debug_info])

    @abstractmethod
    def zks_get_contract_debug_info(self, contract_address: HexAddress):
        return self.make_request(self.zks_get_contract_debug_info_rpc, [contract_address])

    # INFO: might need hexBytes
    @abstractmethod
    def zks_get_transaction_trace(self, transaction_hash: Hash32):
        return self.make_request(self.zks_get_transaction_trace_rpc, [transaction_hash])

    # INFO: might need hexBytes
    @abstractmethod
    def zks_get_all_account_balances(self, address: Address):
        return self.make_request(self.zks_get_all_account_balances_rpc, [address])


class ZkSyncBuilder:
    @classmethod
    def build(cls, web3_module: Web3):
        attach_modules(web3_module, {"zksync": (ZkSyncJsonRPC,)})
