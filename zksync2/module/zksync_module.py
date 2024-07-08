from abc import ABC

import web3
from eth_utils import to_checksum_address, is_address
from eth_utils.curried import apply_formatter_to_array

from eth_utils.curried import apply_formatter_at_index
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.threads import Timeout
from web3.contract import Contract
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
    to_hex_if_integer,
    PYTHONIC_RESULT_FORMATTERS,
    FILTER_RESULT_FORMATTERS,
    apply_module_to_formatters,
    is_not_null,
    to_ascii_if_bytes,
)

from web3.eth import Eth
from web3.types import RPCEndpoint, _Hash32, TxReceipt, BlockIdentifier
from zksync2.core.types import (
    Limit,
    From,
    ContractSourceDebugInfo,
    BridgeAddresses,
    TokenAddress,
    ZksMessageProof,
    BatchDetails,
    BlockRange,
    BlockDetails,
    BaseSystemContractsHashes,
    TransactionDetails,
    ADDRESS_DEFAULT,
    ZkBlockParams,
    L1ToL2Log,
    TransferTransaction,
    TransactionOptions,
    WithdrawTransaction,
    ContractAccountInfo,
    StorageProof,
    ETH_ADDRESS_IN_CONTRACTS, ProtocolVersion, TransactionWithDetailedOutput, FeeParams,
)
from zksync2.core.utils import (
    is_eth,
    MAX_PRIORITY_FEE_PER_GAS,
    LEGACY_ETH_ADDRESS,
    L2_BASE_TOKEN_ADDRESS,
    is_address_eq,
    BOOTLOADER_FORMAL_ADDRESS,
)
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.utils import (
    ERC20Encoder,
    get_erc20_abi,
    icontract_deployer_abi_default,
    l2_bridge_abi_default, l2_shared_bridge_abi_default,
)
from zksync2.module.request_types import *
from zksync2.module.response_types import *
from zksync2.core.types import TransactionReceipt
from eth_typing import Address
from eth_utils import remove_0x_prefix
from eth_utils.toolz import compose
from web3.method import Method, default_root_munger
from typing import Any, Callable, List, Union

from zksync2.transaction.transaction712 import Transaction712
from zksync2.transaction.transaction_builders import (
    TxWithdraw,
    TxFunctionCall,
    TxTransfer,
)

zks_l1_batch_number_rpc = RPCEndpoint("zks_L1BatchNumber")
zks_get_l1_batch_block_range_rpc = RPCEndpoint("zks_getL1BatchBlockRange")
zks_get_l1_batch_details_rpc = RPCEndpoint("zks_getL1BatchDetails")
zks_get_block_details_rpc = RPCEndpoint("zks_getBlockDetails")
zks_get_transaction_details_rpc = RPCEndpoint("zks_getTransactionDetails")
zks_estimate_gas_l1_to_l2_rpc = RPCEndpoint("zks_estimateGasL1ToL2")

zks_estimate_fee_rpc = RPCEndpoint("zks_estimateFee")
zks_main_contract_rpc = RPCEndpoint("zks_getMainContract")
zks_get_token_price_rpc = RPCEndpoint("zks_getTokenPrice")
zks_l1_chain_id_rpc = RPCEndpoint("zks_L1ChainId")
zks_get_all_account_balances_rpc = RPCEndpoint("zks_getAllAccountBalances")
zks_get_bridge_contracts_rpc = RPCEndpoint("zks_getBridgeContracts")
zks_get_l2_to_l1_msg_proof_prc = RPCEndpoint("zks_getL2ToL1MsgProof")
zks_get_l2_to_l1_log_proof_prc = RPCEndpoint("zks_getL2ToL1LogProof")
zks_get_proof_rpc = RPCEndpoint("zks_getProof")
zks_get_base_token_l1_address_rpc = RPCEndpoint("zks_getBaseTokenL1Address")
zks_get_bridgehub_contract_rpc = RPCEndpoint("zks_getBridgehubContract")
zks_get_protocol_version_rpc = RPCEndpoint("zks_getProtocolVersion")
zks_get_confirmed_tokens_rpc = RPCEndpoint("zks_getConfirmedTokens")
zks_send_raw_transaction_with_detailed_output_rpc = RPCEndpoint("zks_sendRawTransactionWithDetailedOutput")
zks_get_fee_params_rpc = RPCEndpoint("zks_getFeeParams")
eth_estimate_gas_rpc = RPCEndpoint("eth_estimateGas")
eth_get_transaction_receipt_rpc = RPCEndpoint("eth_getTransactionReceipt")
eth_get_transaction_by_hash_rpc = RPCEndpoint("eth_getTransactionByHash")

zks_set_contract_debug_info_rpc = RPCEndpoint("zks_setContractDebugInfo")
zks_get_contract_debug_info_rpc = RPCEndpoint("zks_getContractDebugInfo")
zks_get_transaction_trace_rpc = RPCEndpoint("zks_getTransactionTrace")
zks_get_testnet_paymaster_address = RPCEndpoint("zks_getTestnetPaymaster")


def bytes_to_list(v: bytes) -> List[int]:
    return [int(e) for e in v]


def meta_formatter(eip712: EIP712Meta) -> dict:
    ret = {"gasPerPubdata": integer_to_hex(eip712.gas_per_pub_data)}
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
            "paymasterInput": paymaster_input,
        }
    return ret


ZKS_TRANSACTION_PARAMS_FORMATTERS = {
    "data": to_ascii_if_bytes,
    "from": apply_formatter_if(is_address, to_checksum_address),
    "gas": to_hex_if_integer,
    "gasPrice": to_hex_if_integer,
    "maxPriorityFeePerGas": to_hex_if_integer,
    "nonce": to_hex_if_integer,
    "to": apply_formatter_if(is_not_null, to_checksum_address),
    "value": to_hex_if_integer,
    "chainId": to_hex_if_integer,
    "transactionType": to_hex_if_integer,
    "eip712Meta": meta_formatter,
}

zks_transaction_request_formatter = apply_formatters_to_dict(
    ZKS_TRANSACTION_PARAMS_FORMATTERS
)

ZKSYNC_REQUEST_FORMATTERS: [RPCEndpoint, Callable[..., Any]] = {
    eth_estimate_gas_rpc: apply_formatter_at_index(
        zks_transaction_request_formatter, 0
    ),
    zks_estimate_fee_rpc: apply_formatter_at_index(
        zks_transaction_request_formatter, 0
    ),
    zks_estimate_gas_l1_to_l2_rpc: apply_formatter_at_index(
        zks_transaction_request_formatter, 0
    ),
}


def to_token(t: dict) -> Token:
    return Token(
        l1_address=to_checksum_address(t["l1Address"]),
        l2_address=to_checksum_address(t["l2Address"]),
        symbol=t["symbol"],
        decimals=t["decimals"],
    )


def to_bridge_address(t: dict) -> BridgeAddresses:
    return BridgeAddresses(
        erc20_l1_default_bridge=HexStr(to_checksum_address(t["l1Erc20DefaultBridge"])),
        shared_l1_default_bridge=HexStr(
            to_checksum_address(t["l1SharedDefaultBridge"])
        ),
        shared_l2_default_bridge=HexStr(
            to_checksum_address(t["l2SharedDefaultBridge"])
        ),
        erc20_l2_default_bridge=HexStr(to_checksum_address(t["l2Erc20DefaultBridge"])),
        weth_bridge_l1=HexStr(to_checksum_address(t["l1WethBridge"])),
        weth_bridge_l2=HexStr(to_checksum_address(t["l2WethBridge"])),
    )


def to_batch_details(t: dict) -> BatchDetails:
    datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    base_sys_contract_hashes = BaseSystemContractsHashes(
        bootloader=t["baseSystemContractsHashes"]["bootloader"],
        default_aa=t["baseSystemContractsHashes"]["default_aa"],
    )
    return BatchDetails(
        base_system_contracts_hashes=base_sys_contract_hashes,
        commit_tx_hash=t["commitTxHash"],
        committed_at=datetime.strptime(t["committedAt"], datetime_format),
        execute_tx_hash=t["executeTxHash"],
        executed_at=datetime.strptime(t["executedAt"], datetime_format),
        l1_gas_price=t["l1GasPrice"],
        l1_tx_count=t["l1TxCount"],
        l2_fair_gas_price=t["l2FairGasPrice"],
        l2_tx_count=t["l2TxCount"],
        number=t["number"],
        prove_tx_hash=t["proveTxHash"],
        proven_at=datetime.strptime(t["provenAt"], datetime_format),
        root_hash=t["rootHash"],
        status=t["status"],
        timestamp=t["timestamp"],
    )


def to_block_details(t: dict) -> BlockDetails:
    datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    return BlockDetails(
        commit_tx_hash=t["commitTxHash"],
        committed_at=datetime.strptime(t["committedAt"], datetime_format),
        execute_tx_hash=t["executeTxHash"],
        executed_at=datetime.strptime(t["executedAt"], datetime_format),
        l1_tx_count=t["l1TxCount"],
        l2_tx_count=t["l2TxCount"],
        number=t["number"],
        prove_tx_hash=t["proveTxHash"],
        proven_at=datetime.strptime(t["provenAt"], datetime_format),
        root_hash=t["rootHash"],
        status=t["status"],
        timestamp=t["timestamp"],
    )


def to_transaction_details(t: dict) -> TransactionDetails:
    return TransactionDetails(
        ethCommitTxHash=t["ethCommitTxHash"],
        ethExecuteTxHash=t["ethExecuteTxHash"],
        ethProveTxHash=t["ethProveTxHash"],
        fee=t["fee"],
        initiatorAddress=t["initiatorAddress"],
        isL1Originated=t["isL1Originated"],
        receivedAt=t["receivedAt"],
        status=t["status"],
    )


def to_transaction_receipt(t: dict) -> TransactionReceipt:
    logs = []
    for log in t["l2ToL1Logs"]:
        logs.append(to_l2_to_l1_logs(log))
    return TransactionReceipt(
        from_=t["from"],
        to=t["to"],
        block_number=t["blockNumber"],
        l1_batch_tx_index=t["l1BatchTxIndex"],
        l2_to_l1_logs=logs,
    )


def to_l2_to_l1_logs(t: dict) -> L1ToL2Log:
    return L1ToL2Log(
        block_hash=t["blockHash"],
        block_number=t["blockNumber"],
        l1_batch_number=t["l1BatchNumber"],
        transaction_index=t["transactionIndex"],
        transaction_index_in_l1_batch=t["txIndexInL1Batch"] or None,
        transaction_hash=t["transactionHash"],
        transaction_log_index=t["transactionLogIndex"],
        shard_id=t["shardId"],
        is_service=t["isService"],
        sender=t["sender"],
        key=t["key"],
        value=t["value"],
        log_index=t["logIndex"],
    )


def to_transaction_by_hash(t: dict) -> Transaction712:
    return Transaction712()


def to_block_range(t: dict) -> BlockRange:
    return BlockRange(beginning=t["beginning"], end=t["end"])


def to_zks_account_balances(t: dict) -> ZksAccountBalances:
    result = dict()
    for k, v in t.items():
        result[k] = int(v, 16)
    return result


def to_fee(v: dict) -> Fee:
    gas_limit = int(remove_0x_prefix(v["gas_limit"]), 16)
    max_fee_per_gas = int(remove_0x_prefix(v["max_fee_per_gas"]), 16)
    max_priority_fee_per_gas = int(remove_0x_prefix(v["max_priority_fee_per_gas"]), 16)
    gas_per_pubdata_limit = int(remove_0x_prefix(v["gas_per_pubdata_limit"]), 16)
    return Fee(
        gas_limit=gas_limit,
        max_fee_per_gas=max_fee_per_gas,
        max_priority_fee_per_gas=max_priority_fee_per_gas,
        gas_per_pubdata_limit=gas_per_pubdata_limit,
    )


def to_msg_proof(v: dict) -> ZksMessageProof:
    return ZksMessageProof(id=v["id"], proof=v["proof"], root=v["root"])


ZKSYNC_RESULT_FORMATTERS: Dict[RPCEndpoint, Callable[..., Any]] = {
    zks_get_bridge_contracts_rpc: to_bridge_address,
    zks_get_all_account_balances_rpc: to_zks_account_balances,
    zks_estimate_fee_rpc: to_fee,
    zks_get_l2_to_l1_log_proof_prc: to_msg_proof,
    zks_get_l2_to_l1_msg_proof_prc: to_msg_proof,
    zks_get_l1_batch_details_rpc: to_batch_details,
    zks_get_block_details_rpc: to_block_details,
    zks_get_l1_batch_block_range_rpc: to_block_range,
    zks_get_transaction_details_rpc: to_transaction_details,
    eth_get_transaction_receipt_rpc: to_transaction_receipt,
    eth_get_transaction_by_hash_rpc: to_transaction_by_hash,
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
        (ZKSYNC_RESULT_FORMATTERS, PYTHONIC_RESULT_FORMATTERS), method_name
    )
    formatters_requiring_module = combine_formatters(
        (FILTER_RESULT_FORMATTERS,), method_name
    )

    partial_formatters = apply_module_to_formatters(
        formatters_requiring_module, module, method_name
    )
    return compose(*partial_formatters, *formatters)


class ZkSync(Eth, ABC):
    _zks_l1_batch_number: Method[Callable[[], ZksL1BatchNumber]] = Method(
        zks_l1_batch_number_rpc, mungers=None
    )
    _zks_get_l1_batch_block_range: Method[Callable[[int], ZksBlockRange]] = Method(
        zks_get_l1_batch_block_range_rpc, mungers=[default_root_munger]
    )
    _zks_get_l1_batch_details: Method[Callable[[int], ZksBatchDetails]] = Method(
        zks_get_l1_batch_details_rpc,
        mungers=[default_root_munger],
        result_formatters=zksync_get_result_formatters,
    )
    _zks_get_block_details: Method[Callable[[int], ZksBlockDetails]] = Method(
        zks_get_block_details_rpc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
        result_formatters=zksync_get_result_formatters,
    )
    _zks_get_transaction_details: Method[Callable[[str], ZksEstimateFee]] = Method(
        zks_get_transaction_details_rpc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
        result_formatters=zksync_get_result_formatters,
    )
    _zks_get_proof: Method[Callable[[HexStr, List[HexStr], int], StorageProof]] = (
        Method(
            zks_get_proof_rpc,
            mungers=[default_root_munger],
            request_formatters=zksync_get_request_formatters,
        )
    )
    _zks_estimate_gas_l1_to_l2: Method[Callable[[Transaction], int]] = Method(
        zks_estimate_gas_l1_to_l2_rpc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
    )
    _zks_estimate_fee: Method[Callable[[Transaction], ZksEstimateFee]] = Method(
        zks_estimate_fee_rpc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
        result_formatters=zksync_get_result_formatters,
    )

    _zks_main_contract: Method[Callable[[], ZksMainContract]] = Method(
        zks_main_contract_rpc, mungers=None
    )

    _zks_get_base_token_contract_address: Method[Callable[[], ZksBaseToken]] = Method(
        zks_get_base_token_l1_address_rpc, mungers=None
    )

    _zks_get_token_price: Method[Callable[[TokenAddress], ZksTokenPrice]] = Method(
        zks_get_token_price_rpc, mungers=[default_root_munger]
    )

    _zks_l1_chain_id: Method[Callable[[], ZksL1ChainId]] = Method(
        zks_l1_chain_id_rpc, mungers=None
    )

    _zks_get_all_account_balances: Method[Callable[[Address], ZksAccountBalances]] = (
        Method(
            zks_get_all_account_balances_rpc,
            mungers=[default_root_munger],
            result_formatters=zksync_get_result_formatters,
        )
    )

    _zks_get_bridge_contracts: Method[Callable[[], ZksBridgeAddresses]] = Method(
        zks_get_bridge_contracts_rpc,
        mungers=[default_root_munger],
        result_formatters=zksync_get_result_formatters,
    )

    _zks_get_l2_to_l1_msg_proof: Method[
        Callable[[int, Address, str, Optional[int]], ZksMessageProof]
    ] = Method(
        zks_get_l2_to_l1_msg_proof_prc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
        result_formatters=zksync_get_result_formatters,
    )

    _zks_get_bridgehub_contract_address: Method[
        Callable[[int, Address, str, Optional[int]], ZksMessageProof]
    ] = Method(
        zks_get_bridgehub_contract_rpc,
        mungers=[default_root_munger],
    )

    _zks_get_l2_to_l1_log_proof: Method[
        Callable[[Address, Optional[int]], ZksMessageProof]
    ] = Method(
        zks_get_l2_to_l1_log_proof_prc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
        result_formatters=zksync_get_result_formatters,
    )

    _zks_get_protocol_version: Method[
        Callable[[Optional[int]], ProtocolVersion]
    ] = Method(
        zks_get_protocol_version_rpc,
        mungers=[default_root_munger],
    )

    _zks_get_confirmed_tokens: Method[
        Callable[[int, int], List[Token]]
    ] = Method(
        zks_get_confirmed_tokens_rpc,
        mungers=[default_root_munger],
    )

    _zks_send_raw_transaction_with_detailed_output: Method[
        Callable[[Union[HexStr, bytes]], TransactionWithDetailedOutput]
    ] = Method(
        zks_send_raw_transaction_with_detailed_output_rpc,
        mungers=[default_root_munger],
    )

    _zks_get_fee_params: Method[
        Callable[[], FeeParams]
    ] = Method(
        zks_get_fee_params_rpc,
        mungers=[default_root_munger],
    )

    _eth_estimate_gas: Method[Callable[[Transaction], int]] = Method(
        eth_estimate_gas_rpc,
        mungers=[default_root_munger],
        request_formatters=zksync_get_request_formatters,
    )
    _eth_get_transaction_receipt: Method[Callable[[HexStr], ZksTransactionReceipt]] = (
        Method(
            eth_get_transaction_receipt_rpc,
            mungers=[default_root_munger],
            result_formatters=zksync_get_result_formatters,
        )
    )
    _eth_get_transaction_by_hash: Method[Callable[[HexStr], ZksTransactions]] = Method(
        eth_get_transaction_by_hash_rpc,
        mungers=[default_root_munger],
        result_formatters=zksync_get_result_formatters,
    )
    # TODO: implement it
    _zks_set_contract_debug_info: Method[
        Callable[[Address, ContractSourceDebugInfo], ZksSetContractDebugInfoResult]
    ] = Method(zks_set_contract_debug_info_rpc, mungers=[default_root_munger])
    _zks_get_contract_debug_info: Method[
        Callable[[Address], ContractSourceDebugInfo]
    ] = Method(zks_get_contract_debug_info_rpc, mungers=[default_root_munger])

    _zks_get_transaction_trace: Method[Callable[[Address], ZksTransactionTrace]] = (
        Method(zks_get_transaction_trace_rpc, mungers=[default_root_munger])
    )

    _zks_get_testnet_paymaster_address: Method[Callable[[], HexStr]] = Method(
        zks_get_testnet_paymaster_address, mungers=[default_root_munger]
    )

    def __init__(self, web3: "Web3"):
        super(ZkSync, self).__init__(web3)
        self.main_contract_address = None
        self.bridgehub_contract_address = None
        self.bridge_addresses = None
        self.base_token = None

    def zks_l1_batch_number(self) -> int:
        return int(self._zks_l1_batch_number(), 16)

    def zks_get_l1_batch_block_range(self, l1_batch_number: int) -> BlockRange:
        return self._zks_get_l1_batch_block_range(l1_batch_number)

    def zks_get_l1_batch_details(self, l1_batch_number: int) -> BatchDetails:
        return self._zks_get_l1_batch_details(l1_batch_number)

    def zks_get_block_details(self, block: int) -> BlockDetails:
        return self._zks_get_block_details(block)

    def zks_get_transaction_details(self, txHash: str) -> TransactionDetails:
        return self._zks_get_transaction_details(txHash)

    def zks_estimate_gas_l1_to_l2(self, transaction: Transaction) -> int:
        return int(self._zks_estimate_gas_l1_to_l2(transaction), 16)

    def zks_get_proof(self, address: HexStr, key: List[HexStr], l1_batch_number: int):
        return self._zks_get_proof(address, key, l1_batch_number)

    def zks_get_protocol_version(self, id: int = None) -> ProtocolVersion:
        """
        Returns the protocol version.

        Calls the zks_getProtocolVersion JSON-RPC method.
        (Refer to: https://docs.zksync.io/build/api.html#zks_getprotocolversion)

        :param id: Specific version ID (optional).
        """

        return self._zks_get_protocol_version(id)

    def zks_get_confirmed_tokens(self, start: int = 0, limit: int = 255) -> ProtocolVersion:
        """
        Returns confirmed tokens. A confirmed token is any token bridged to ZKsync Era via the official bridge.

        Calls the zks_getConfirmedTokens JSON-RPC method.
        (Refer to: https://docs.zksync.io/build/api.html#zks_getconfirmedtokens)

        :param start: The token ID from which to start.
        :param limit: The maximum number of tokens to list.
        """

        return self._zks_get_confirmed_tokens(start, limit)

    def zks_send_raw_transaction_with_detailed_output(self, tx: Union[HexStr, bytes]) -> ProtocolVersion:
        """
        Executes a transaction and returns its hash, storage logs, and events that would have been generated if the
        transaction had already been included in the block. The API has a similar behaviour to `eth_sendRawTransaction`
        but with some extra data returned from it.

        With this API, consumer apps can apply "optimistic" events in their applications instantly without having to
        wait for ZKsync block confirmation time.

        It’s expected that the optimistic logs of two uncommitted transactions that modify the same state will not
        have causal relationships between each other.

        Calls the zks_sendRawTransactionWithDetailedOutput JSON-RPC method.
        (Refer to: https://docs.zksync.io/build/api.html#zks_sendRawTransactionWithDetailedOutput)

        :param tx: The signed transaction that needs to be broadcasted.
        """
        return self._zks_send_raw_transaction_with_detailed_output(tx)

    def zks_estimate_gas_transfer(
        self, transaction: Transaction, token_address: HexStr = ADDRESS_DEFAULT
    ) -> int:
        if token_address is not None and not is_eth(token_address):
            transfer_params = (transaction["to"], transaction["value"])
            transaction["value"] = 0
            contract = self.contract(
                Web3.to_checksum_address(token_address), abi=get_erc20_abi()
            )
            transaction["data"] = contract.encodeABI("transfer", args=transfer_params)
            transaction["nonce"] = self.get_transaction_count(
                transaction["from_"], ZkBlockParams.COMMITTED.value
            )

        return self.eth_estimate_gas(transaction)

    def zks_estimate_l1_to_l2_execute(self, transaction: Transaction) -> int:
        if transaction["from"] is None:
            transaction["from"] = self.account.create().address

        return self.zks_estimate_gas_l1_to_l2(transaction)

    def zks_estimate_fee(self, transaction: Transaction) -> Fee:
        return self._zks_estimate_fee(transaction)

    def zks_main_contract(self) -> HexStr:
        if self.main_contract_address is None:
            self.main_contract_address = self._zks_main_contract()
        return self.main_contract_address

    def zks_get_base_token_contract_address(self):
        """Returns the L1 base token address."""
        if self.base_token is None:
            self.base_token = self._zks_get_base_token_contract_address()
        return self.base_token

    def is_eth_based_chain(self) -> bool:
        return is_address_eq(
            self.zks_get_base_token_contract_address(), ETH_ADDRESS_IN_CONTRACTS
        )

    def zks_get_bridgehub_contract_address(self) -> HexStr:
        if self.bridgehub_contract_address is None:
            self.bridgehub_contract_address = self._zks_get_bridgehub_contract_address()
        return self.bridgehub_contract_address

    def zks_get_token_price(self, token_address: TokenAddress) -> Decimal:
        return self._zks_get_token_price(token_address)

    def zks_l1_chain_id(self) -> int:
        return int(self._zks_l1_chain_id(), 16)

    def zks_get_balance(
        self,
        address: HexStr,
        block_tag=ZkBlockParams.COMMITTED.value,
        token_address: HexStr = None,
    ) -> int:
        if token_address is None:
            token_address = L2_BASE_TOKEN_ADDRESS
        elif (
            token_address == LEGACY_ETH_ADDRESS
            or token_address == ETH_ADDRESS_IN_CONTRACTS
        ):
            token_address = self.l2_token_address(ETH_ADDRESS_IN_CONTRACTS)
        if token_address == L2_BASE_TOKEN_ADDRESS:
            return self.get_balance(to_checksum_address(address), block_tag)

        try:
            token = self.contract(
                Web3.to_checksum_address(token_address), abi=get_erc20_abi()
            )
            return token.functions.balanceOf(address).call()
        except:
            return 0

    def is_base_token(self, token: HexStr):
        return is_address_eq(
            token, self.zks_get_base_token_contract_address()
        ) or is_address_eq(token, L2_BASE_TOKEN_ADDRESS)

    def l1_token_address(self, token: HexStr) -> HexStr:
        """
        Returns the L1 token address equivalent for a L2 token address as they are not equal.
        ETH address is set to zero address.

        :param token: The address of the token on L2.
        """
        if token == LEGACY_ETH_ADDRESS:
            return LEGACY_ETH_ADDRESS

        bridge_address = self.zks_get_bridge_contracts()
        shared_bridge = self.contract(
            Web3.to_checksum_address(bridge_address.shared_l2_default_bridge),
            abi=l2_bridge_abi_default(),
        )

        return shared_bridge.functions.l1TokenAddress(token).call()

    def l2_token_address(self, token: HexStr, bridge_address: HexStr = None) -> HexStr:
        """
        Returns the L2 token address equivalent for a L1 token address as they are not equal.
        ETH address is set to zero address.

        :param token: The address of the token on L1.
        :param bridge_address: The address of custom bridge, which will be used to get l2 token address.
        """
        if token == ADDRESS_DEFAULT:
            token = ETH_ADDRESS_IN_CONTRACTS
        base_token = self.zks_get_base_token_contract_address()
        if token.lower() == base_token.lower():
            return L2_BASE_TOKEN_ADDRESS

        if bridge_address is None:
            bridge_address = self.zks_get_bridge_contracts()
        l2_shared_bridge = self.contract(
            Web3.to_checksum_address(bridge_address.shared_l2_default_bridge),
            abi=l2_bridge_abi_default(),
        )

        return l2_shared_bridge.functions.l2TokenAddress(token).call()

    def zks_get_all_account_balances(self, addr: Address) -> ZksAccountBalances:
        return self._zks_get_all_account_balances(addr)

    def zks_get_bridge_contracts(self) -> BridgeAddresses:
        if self.bridge_addresses is None:
            self.bridge_addresses = self._zks_get_bridge_contracts()
        return self.bridge_addresses

    def zks_get_l2_to_l1_msg_proof(
        self, block: int, sender: HexStr, message: str, l2log_pos: Optional[int]
    ) -> ZksMessageProof:
        return self._zks_get_l2_to_l1_msg_proof(block, sender, message, l2log_pos)

    def zks_get_log_proof(self, tx_hash: HexStr, index: int = None) -> ZksMessageProof:
        return self._zks_get_l2_to_l1_log_proof(tx_hash, index)

    def zks_get_testnet_paymaster_address(self) -> HexStr:
        return Web3.to_checksum_address(self._zks_get_testnet_paymaster_address())

    def eth_estimate_gas(self, tx: Transaction) -> int:
        return self._eth_estimate_gas(tx)

    def eth_get_transaction_receipt(self, tx: HexStr) -> TransactionReceipt:
        return self._eth_get_transaction_receipt(tx)

    def eth_get_transaction_by_hash(self, tx: HexStr) -> Transaction712:
        return self._eth_get_transaction_by_hash(tx)

    @staticmethod
    def get_l2_hash_from_priority_op(tx_receipt: TxReceipt, contract: Contract):
        logs = contract.events["NewPriorityRequest"]().process_receipt(tx_receipt)
        if len(logs):
            return logs[0].args.txHash
        else:
            raise RuntimeError("Wrong transaction received")

    def get_l2_transaction_from_priority_op(self, tx_receipt, main_contract: Contract):
        l2_hash = self.get_l2_hash_from_priority_op(tx_receipt, main_contract)
        self.wait_for_transaction_receipt(l2_hash)
        return self.get_transaction(l2_hash)

    def _get_priority_op_confirmation_l2_to_l1_log(
        self, tx_hash: HexStr, index: int = 0
    ):
        receipt = self.eth_get_transaction_receipt(tx_hash)
        msgs = []
        for i, e in enumerate(receipt.l2_to_l1_logs):
            if e.sender.lower() == BOOTLOADER_FORMAL_ADDRESS:
                msgs.append((i, e))

        l2_to_l1_log_index, log = msgs[index]

        return l2_to_l1_log_index, log, receipt.l1_batch_tx_index

    def get_priority_op_confirmation(self, tx_hash: HexStr, index: int = 0):
        l2_to_l1_log_index, log, l1_batch_tx_index = (
            self._get_priority_op_confirmation_l2_to_l1_log(tx_hash, index)
        )
        proof = self.zks_get_log_proof(tx_hash, l2_to_l1_log_index)

        return log.l1_batch_number, proof.id, l1_batch_tx_index, proof.proof

    def wait_for_transaction_receipt(
        self, transaction_hash: _Hash32, timeout: float = 120, poll_latency: float = 0.1
    ) -> TxReceipt:
        try:
            with Timeout(timeout) as _timeout:
                while True:
                    try:
                        tx_receipt = self.get_transaction_receipt(transaction_hash)
                    except TransactionNotFound:
                        tx_receipt = None
                    if tx_receipt is not None and tx_receipt["blockHash"] is not None:
                        break
                    _timeout.sleep(poll_latency)
            return tx_receipt

        except Timeout:
            raise TimeExhausted(
                f"Transaction {HexBytes(transaction_hash) !r} is not in the chain after {timeout} seconds"
            )

    def wait_finalized(
        self, transaction_hash: _Hash32, timeout: float = 120, poll_latency: float = 0.1
    ) -> TxReceipt:
        try:
            with Timeout(timeout) as _timeout:
                while True:
                    try:
                        block = self.get_block("finalized")
                        tx_receipt = self.get_transaction_receipt(transaction_hash)
                    except TransactionNotFound:
                        tx_receipt = None
                    if (
                        tx_receipt is not None
                        and tx_receipt["blockHash"] is not None
                        and block["number"] >= tx_receipt["blockNumber"]
                    ):
                        break
                    _timeout.sleep(poll_latency)
            return tx_receipt

        except Timeout:
            raise TimeExhausted(
                f"Transaction {HexBytes(transaction_hash) !r} is not in the chain after {timeout} seconds"
            )

    def get_withdraw_transaction(
        self,
        tx: WithdrawTransaction,
        from_: HexStr,
    ) -> TxWithdraw:
        token = tx.token
        if token is None:
            token = L2_BASE_TOKEN_ADDRESS
        if token == LEGACY_ETH_ADDRESS or token == ETH_ADDRESS_IN_CONTRACTS:
            token = self.l2_token_address(ETH_ADDRESS_IN_CONTRACTS)
        if tx.options is None:
            tx.options = TransactionOptions()

        return TxWithdraw(
            web3=self,
            chain_id=tx.options.chain_id,
            nonce=tx.options.nonce,
            to=tx.to,
            amount=tx.amount,
            gas_limit=tx.options.gas_limit,
            max_fee_per_gas=tx.options.max_fee_per_gas,
            max_priority_fee_per_gas=tx.options.max_priority_fee_per_gas,
            token=token,
            bridge_address=tx.bridge_address,
            from_=from_,
            paymaster_params=tx.paymaster_params,
        )

    def get_transfer_transaction(
        self, tx: TransferTransaction, from_: HexStr
    ) -> TxTransfer:
        token = tx.token_address
        if token is None:
            token = L2_BASE_TOKEN_ADDRESS
        elif token == LEGACY_ETH_ADDRESS or token == ETH_ADDRESS_IN_CONTRACTS:
            token = self.l2_token_address(ETH_ADDRESS_IN_CONTRACTS)

        if tx.options is None:
            tx.options = TransactionOptions()
        if tx.options.chain_id is None:
            tx.options.chain_id = self.chain_id
        if tx.options.nonce is None:
            tx.options.nonce = self.get_transaction_count(
                Web3.to_checksum_address(from_), ZkBlockParams.LATEST.value
            )
        if tx.options.gas_price is None:
            tx.options.gas_price = self.gas_price
        if tx.options.max_fee_per_gas is None:
            tx.options.max_fee_per_gas = 0
        if tx.options.max_priority_fee_per_gas is None:
            tx.options.max_priority_fee_per_gas = 0
        if tx.options.gas_limit is None:
            tx.options.gas_limit = 0

        call_data = "0x"
        if not is_eth(token):
            transfer_params = (tx.to, tx.amount)
            contract = self.contract(
                Web3.to_checksum_address(tx.token_address), abi=get_erc20_abi()
            )
            call_data = contract.encodeABI("transfer", transfer_params)

        transaction = TxTransfer(
            web3=self,
            token=token,
            chain_id=tx.options.chain_id,
            nonce=tx.options.nonce,
            from_=from_,
            to=tx.to,
            data=call_data,
            value=tx.amount,
            gas_limit=tx.options.gas_limit,
            max_fee_per_gas=tx.options.max_fee_per_gas,
            max_priority_fee_per_gas=tx.options.max_priority_fee_per_gas,
            gas_per_pub_data=tx.gas_per_pub_data,
            paymaster_params=tx.paymaster_params,
        )

        return transaction

    def get_contract_account_info(self, address: HexStr) -> ContractAccountInfo:
        deployer = self.contract(
            address=Web3.to_checksum_address(
                ZkSyncAddresses.CONTRACT_DEPLOYER_ADDRESS.value
            ),
            abi=icontract_deployer_abi_default(),
        )
        data = deployer.functions.getAccountInfo(
            Web3.to_checksum_address(address)
        ).call()
        return ContractAccountInfo(
            account_abstraction_version=data[0], account_nonce_ordering=data[1]
        )

    def is_l2_bridge_legacy(self, address: HexStr) -> bool:
        """
        Returns true if the passed bridge address is legacy and false if it is a shared bridge.

        :param address: The bridge address.
        """
        bridge = self.contract(
            address=Web3.to_checksum_address(address),
            abi=l2_shared_bridge_abi_default()
        )
        try:
            bridge.functions.l1SharedBridge().call()
            return False
        except:
            pass

        return True
