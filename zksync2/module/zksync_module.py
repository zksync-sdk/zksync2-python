from abc import ABC
from eth_utils import to_checksum_address, is_address
from eth_utils.curried import apply_formatter_to_array

from eth_utils.curried import apply_formatter_at_index
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.threads import Timeout
from web3.exceptions import TransactionNotFound, TimeExhausted
from web3.module import Module
from web3._utils.formatters import integer_to_hex
from web3._utils.method_formatters import (
    ABI_REQUEST_FORMATTERS,
    METHOD_NORMALIZERS,
    PYTHONIC_REQUEST_FORMATTERS,
    combine_formatters,
    apply_formatter_if,
    apply_formatters_to_dict,
    apply_list_to_array_formatter,
    to_hex_if_integer, PYTHONIC_RESULT_FORMATTERS, FILTER_RESULT_FORMATTERS,
    apply_module_to_formatters, is_not_null, to_ascii_if_bytes
)

from web3.eth import Eth
from web3.types import RPCEndpoint, _Hash32, TxReceipt
from zksync2.core.types import Limit, From, ContractSourceDebugInfo, \
    BridgeAddresses, TokenAddress, ZksMessageProof
from zksync2.manage_contracts.zksync_contract import ZkSyncContract
from zksync2.module.request_types import *
from zksync2.module.response_types import *
from eth_typing import Address
from eth_utils import remove_0x_prefix
from eth_utils.toolz import compose
from web3.method import Method, default_root_munger
from typing import Any, Callable, List, Union

zks_estimate_fee_rpc = RPCEndpoint("zks_estimateFee")
zks_main_contract_rpc = RPCEndpoint("zks_getMainContract")
zks_get_confirmed_tokens_rpc = RPCEndpoint("zks_getConfirmedTokens")
zks_get_token_price_rpc = RPCEndpoint("zks_getTokenPrice")
zks_l1_chain_id_rpc = RPCEndpoint("zks_L1ChainId")
zks_get_all_account_balances_rpc = RPCEndpoint("zks_getAllAccountBalances")
zks_get_bridge_contracts_rpc = RPCEndpoint("zks_getBridgeContracts")
zks_get_l2_to_l1_msg_proof_prc = RPCEndpoint("zks_getL2ToL1MsgProof")
zks_get_l2_to_l1_log_proof_prc = RPCEndpoint("zks_getL2ToL1LogProof")
eth_estimate_gas_rpc = RPCEndpoint("eth_estimateGas")

zks_set_contract_debug_info_rpc = RPCEndpoint("zks_setContractDebugInfo")
zks_get_contract_debug_info_rpc = RPCEndpoint("zks_getContractDebugInfo")
zks_get_transaction_trace_rpc = RPCEndpoint("zks_getTransactionTrace")
zks_get_testnet_paymaster_address = RPCEndpoint("zks_getTestnetPaymaster")


def bytes_to_list(v: bytes) -> List[int]:
    return [int(e) for e in v]


def meta_formatter(eip712: EIP712Meta) -> dict:
    ret = {
        "gasPerPubdata": integer_to_hex(eip712.gas_per_pub_data)
    }
    if eip712.custom_signature is not None:
        ret["customSignature"] = eip712.custom_signature.hex()

    factory_formatter = apply_formatter_to_array(bytes_to_list)
    if eip712.factory_deps is not None:
        ret["factoryDeps"] = factory_formatter(eip712.factory_deps)

    pp_params = eip712.paymaster_params
    if pp_params is not None:
        paymaster_input = bytes_to_list(pp_params.paymaster_input)
        ret["paymasterParams"] = {
            "paymaster": pp_params.paymaster,
            "paymasterInput": paymaster_input
        }
    return ret


ZKS_TRANSACTION_PARAMS_FORMATTERS = {
    'data': to_ascii_if_bytes,
    'from': apply_formatter_if(is_address, to_checksum_address),
    'gas': to_hex_if_integer,
    'gasPrice': to_hex_if_integer,
    'maxPriorityFeePerGas': to_hex_if_integer,
    'nonce': to_hex_if_integer,
    'to': apply_formatter_if(is_not_null, to_checksum_address),
    'value': to_hex_if_integer,
    'chainId': to_hex_if_integer,
    'transactionType': to_hex_if_integer,
    'eip712Meta': meta_formatter,
}

zks_transaction_request_formatter = apply_formatters_to_dict(ZKS_TRANSACTION_PARAMS_FORMATTERS)

ZKSYNC_REQUEST_FORMATTERS: [RPCEndpoint, Callable[..., Any]] = {
    eth_estimate_gas_rpc: apply_formatter_at_index(zks_transaction_request_formatter, 0),
    zks_estimate_fee_rpc: apply_formatter_at_index(zks_transaction_request_formatter, 0),
}


def to_token(t: dict) -> Token:
    return Token(l1_address=to_checksum_address(t["l1Address"]),
                 l2_address=to_checksum_address(t["l2Address"]),
                 symbol=t["symbol"],
                 decimals=t["decimals"])


def to_bridge_address(t: dict) -> BridgeAddresses:
    return BridgeAddresses(
        erc20_l1_default_bridge=HexStr(to_checksum_address(t["l1Erc20DefaultBridge"])),
        erc20_l2_default_bridge=HexStr(to_checksum_address(t["l2Erc20DefaultBridge"]))
    )


def to_zks_account_balances(t: dict) -> ZksAccountBalances:
    result = dict()
    for k, v in t.items():
        result[k] = int(v, 16)
    return result


def to_fee(v: dict) -> Fee:
    gas_limit = int(remove_0x_prefix(v['gas_limit']), 16)
    max_fee_per_gas = int(remove_0x_prefix(v['max_fee_per_gas']), 16)
    max_priority_fee_per_gas = int(remove_0x_prefix(v['max_priority_fee_per_gas']), 16)
    gas_per_pubdata_limit = int(remove_0x_prefix(v['gas_per_pubdata_limit']), 16)
    return Fee(gas_limit=gas_limit,
               max_fee_per_gas=max_fee_per_gas,
               max_priority_fee_per_gas=max_priority_fee_per_gas,
               gas_per_pubdata_limit=gas_per_pubdata_limit)


def to_msg_proof(v: dict) -> ZksMessageProof:
    return ZksMessageProof(id=v['id'],
                           proof=v['proof'],
                           root=v['root'])


ZKSYNC_RESULT_FORMATTERS: Dict[RPCEndpoint, Callable[..., Any]] = {
    zks_get_confirmed_tokens_rpc: apply_list_to_array_formatter(to_token),
    zks_get_bridge_contracts_rpc: to_bridge_address,
    zks_get_all_account_balances_rpc: to_zks_account_balances,
    zks_estimate_fee_rpc: to_fee,
    zks_get_l2_to_l1_log_proof_prc: to_msg_proof,
    zks_get_l2_to_l1_msg_proof_prc: to_msg_proof
}


def zksync_get_request_formatters(
        method_name: Union[RPCEndpoint, Callable[..., RPCEndpoint]]
) -> Dict[str, Callable[..., Any]]:
    request_formatter_maps = (
        ZKSYNC_REQUEST_FORMATTERS,
        ABI_REQUEST_FORMATTERS,
        METHOD_NORMALIZERS,
        PYTHONIC_REQUEST_FORMATTERS,
    )
    formatters = combine_formatters(request_formatter_maps, method_name)
    return compose(*formatters)


def zksync_get_result_formatters(
        method_name: Union[RPCEndpoint, Callable[..., RPCEndpoint]],
        module: "Module",
) -> Dict[str, Callable[..., Any]]:
    # formatters = combine_formatters((PYTHONIC_RESULT_FORMATTERS,), method_name)
    # formatters_requiring_module = combine_formatters(
    #     (FILTER_RESULT_FORMATTERS,), method_name
    # )
    # partial_formatters = apply_module_to_formatters(
    #     formatters_requiring_module, module, method_name
    # )
    # return compose(*partial_formatters, *formatters)

    formatters = combine_formatters(
        (ZKSYNC_RESULT_FORMATTERS,
         PYTHONIC_RESULT_FORMATTERS),
        method_name
    )
    formatters_requiring_module = combine_formatters(
        (FILTER_RESULT_FORMATTERS,),
        method_name
    )

    partial_formatters = apply_module_to_formatters(
        formatters_requiring_module,
        module,
        method_name
    )
    return compose(*partial_formatters, *formatters)


class ZkSync(Eth, ABC):
    _zks_estimate_fee: Method[Callable[[Transaction], ZksEstimateFee]] = Method(
        zks_estimate_fee_rpc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
        result_formatters=zksync_get_result_formatters
    )

    _zks_main_contract: Method[Callable[[], ZksMainContract]] = Method(
        zks_main_contract_rpc,
        mungers=None
    )

    _zks_get_confirmed_tokens: Method[Callable[[From, Limit], ZksTokens]] = Method(
        zks_get_confirmed_tokens_rpc,
        mungers=[default_root_munger],
        result_formatters=zksync_get_result_formatters
    )

    _zks_get_token_price: Method[Callable[[TokenAddress], ZksTokenPrice]] = Method(
        zks_get_token_price_rpc,
        mungers=[default_root_munger]
    )

    _zks_l1_chain_id: Method[Callable[[], ZksL1ChainId]] = Method(
        zks_l1_chain_id_rpc,
        mungers=None
    )

    _zks_get_all_account_balances: Method[Callable[[Address], ZksAccountBalances]] = Method(
        zks_get_all_account_balances_rpc,
        mungers=[default_root_munger],
        result_formatters=zksync_get_result_formatters
    )

    _zks_get_bridge_contracts: Method[Callable[[], ZksBridgeAddresses]] = Method(
        zks_get_bridge_contracts_rpc,
        mungers=[default_root_munger],
        result_formatters=zksync_get_result_formatters
    )

    _zks_get_l2_to_l1_msg_proof: Method[Callable[[int, Address, str, Optional[int]], ZksMessageProof]] = Method(
        zks_get_l2_to_l1_msg_proof_prc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
        result_formatters=zksync_get_result_formatters
    )

    _zks_get_l2_to_l1_log_proof: Method[Callable[[Address, Optional[int]], ZksMessageProof]] = Method(
        zks_get_l2_to_l1_log_proof_prc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
        result_formatters=zksync_get_result_formatters
    )

    _eth_estimate_gas: Method[Callable[[Transaction], int]] = Method(
        eth_estimate_gas_rpc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters
    )

    # TODO: implement it
    _zks_set_contract_debug_info: Method[Callable[[Address,
                                                   ContractSourceDebugInfo],
                                                  ZksSetContractDebugInfoResult]] = Method(
        zks_set_contract_debug_info_rpc,
        mungers=[default_root_munger]
    )
    _zks_get_contract_debug_info: Method[Callable[[Address], ContractSourceDebugInfo]] = Method(
        zks_get_contract_debug_info_rpc,
        mungers=[default_root_munger]
    )

    _zks_get_transaction_trace: Method[Callable[[Address], ZksTransactionTrace]] = Method(
        zks_get_transaction_trace_rpc,
        mungers=[default_root_munger]
    )

    _zks_get_testnet_paymaster_address: Method[Callable[[], HexStr]] = Method(
        zks_get_testnet_paymaster_address,
        mungers=[default_root_munger]
    )

    def __init__(self, web3: "Web3"):
        super(ZkSync, self).__init__(web3)
        self.main_contract_address = None
        self.bridge_addresses = None

    def zks_estimate_fee(self, transaction: Transaction) -> Fee:
        return self._zks_estimate_fee(transaction)

    def zks_main_contract(self) -> HexStr:
        if self.main_contract_address is None:
            self.main_contract_address = self._zks_main_contract()
        return self.main_contract_address

    def zks_get_confirmed_tokens(self, offset: From, limit: Limit) -> List[Token]:
        return self._zks_get_confirmed_tokens(offset, limit)

    def zks_get_token_price(self, token_address: TokenAddress) -> Decimal:
        return self._zks_get_token_price(token_address)

    def zks_l1_chain_id(self) -> int:
        return self._zks_l1_chain_id()

    def zks_get_all_account_balances(self, addr: Address) -> ZksAccountBalances:
        return self._zks_get_all_account_balances(addr)

    def zks_get_bridge_contracts(self) -> BridgeAddresses:
        if self.bridge_addresses is None:
            self.bridge_addresses = self._zks_get_bridge_contracts()
        return self.bridge_addresses

    def zks_get_l2_to_l1_msg_proof(self,
                                   block: int,
                                   sender: HexStr,
                                   message: str,
                                   l2log_pos: Optional[int]) -> ZksMessageProof:
        return self._zks_get_l2_to_l1_msg_proof(block, sender, message, l2log_pos)

    def zks_get_log_proof(self, tx_hash: HexStr, index: int = None) -> ZksMessageProof:
        return self._zks_get_l2_to_l1_log_proof(tx_hash, index)

    def zks_get_testnet_paymaster_address(self) -> HexStr:
        return Web3.to_checksum_address(self._zks_get_testnet_paymaster_address())

    def eth_estimate_gas(self, tx: Transaction) -> int:
        return self._eth_estimate_gas(tx)

    @staticmethod
    def get_l2_hash_from_priority_op(tx_receipt: TxReceipt, main_contract: ZkSyncContract):
        logs = main_contract.parse_events(tx_receipt, "NewPriorityRequest")
        if len(logs):
            return logs[0].args.txHash
        else:
            raise RuntimeError("Wrong transaction received")

    def get_l2_transaction_from_priority_op(self, tx_receipt, main_contract: ZkSyncContract):
        l2_hash = self.get_l2_hash_from_priority_op(tx_receipt, main_contract)
        self.wait_for_transaction_receipt(l2_hash)
        return self.get_transaction(l2_hash)

    def get_priority_op_response(self, tx_receipt, main_contract: ZkSyncContract):
        tx = self.get_l2_transaction_from_priority_op(tx_receipt, main_contract)
        return tx

    def wait_for_transaction_receipt(self,
                                     transaction_hash: _Hash32,
                                     timeout: float = 120,
                                     poll_latency: float = 0.1) -> TxReceipt:
        try:
            with Timeout(timeout) as _timeout:
                while True:
                    try:
                        tx_receipt = self.get_transaction_receipt(transaction_hash)
                    except TransactionNotFound:
                        tx_receipt = None
                    if tx_receipt is not None and \
                            tx_receipt["blockHash"] is not None:
                        break
                    _timeout.sleep(poll_latency)
            return tx_receipt

        except Timeout:
            raise TimeExhausted(
                f"Transaction {HexBytes(transaction_hash) !r} is not in the chain after {timeout} seconds"
            )

    def wait_finalized(self,
                       transaction_hash: _Hash32,
                       timeout: float = 120,
                       poll_latency: float = 0.1) -> TxReceipt:
        try:
            with Timeout(timeout) as _timeout:
                while True:
                    try:
                        block = self.get_block("finalized")
                        tx_receipt = self.get_transaction_receipt(transaction_hash)
                    except TransactionNotFound:
                        tx_receipt = None
                    if tx_receipt is not None and \
                            tx_receipt["blockHash"] is not None and \
                            block["number"] >= tx_receipt["blockNumber"]:
                        break
                    _timeout.sleep(poll_latency)
            return tx_receipt

        except Timeout:
            raise TimeExhausted(
                f"Transaction {HexBytes(transaction_hash) !r} is not in the chain after {timeout} seconds"
            )
