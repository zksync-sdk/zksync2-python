from abc import ABC

from web3 import Web3
from web3.eth import Eth
from web3.types import RPCEndpoint
from zk_types.zk_types import *
from eth_typing import Address, HexAddress
# from web3.module import Module
from web3.method import Method, default_root_munger
from typing import Any, Callable, List


class ZkSync(Eth, ABC):
    zks_main_contract_rpc = RPCEndpoint("zks_getMainContract")
    zks_estimate_fee_rpc = RPCEndpoint("zks_estimateFee")
    zks_get_l1_withdraw_tx_rpc = RPCEndpoint("zks_getL1WithdrawalTx")
    zks_get_account_transactions_rpc = RPCEndpoint("zks_getAccountTransactions")
    zks_get_confirmed_tokens_rpc = RPCEndpoint("zks_getConfirmedTokens")
    zks_is_token_liquid_rpc = RPCEndpoint("zks_isTokenLiquid")
    zks_get_token_price_prc = RPCEndpoint("zks_getTokenPrice")
    zks_l1_chain_id_rpc = RPCEndpoint("zks_L1ChainId")
    zks_eth_get_balance = RPCEndpoint("eth_getBalance")

    # TODO: implement it later
    zks_set_contract_debug_info_rpc = RPCEndpoint("zks_setContractDebugInfo")
    zks_get_contract_debug_info_rpc = RPCEndpoint("zks_getContractDebugInfo")
    zks_get_transaction_trace_rpc = RPCEndpoint("zks_getTransactionTrace")

    _zks_main_contract: Method[Callable[[], HexStr]] = Method(
        zks_main_contract_rpc,
        mungers=None
    )

    _zks_estimate_fee: Method[Callable[[Transaction], Fee]] = Method(
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

    _zks_eth_get_balance: Method[Callable[[Address, Any, TokenAddress], Any]] = Method(
        zks_eth_get_balance,
        mungers=[default_root_munger]
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

    def zks_estimate_fee(self, transaction: Transaction) -> Fee:
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

    def eth_get_balance(self, address: Address, default_block, token_address: TokenAddress) -> Any:
        return self._zks_eth_get_balance(address, default_block, token_address)

    # TODO: implement it later
    # def zks_set_contract_debug_info(self, contract_address: ContractAddress, debug_info: ContractDebugInfo) -> Any:
    #     return self._zks_set_contract_debug_info([contract_address, debug_info])
    #
    # def zks_get_contract_debug_info(self, contract_address: ContractAddress):
    #     pass


