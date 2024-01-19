from eth_typing import HexStr
from web3.types import Nonce

from zksync2.core.types import (
    DepositTransaction,
    RequestExecuteCallMsg,
    TransactionOptions,
)
from zksync2.transaction.transaction712 import Transaction712


def deposit_to_request_execute(
    transaction: DepositTransaction,
) -> RequestExecuteCallMsg:
    return RequestExecuteCallMsg(
        contract_address=transaction.to,
        call_data=HexStr("0x"),
        l2_gas_limit=transaction.l2_gas_limit,
        l2_value=transaction.amount,
        operator_tip=transaction.operator_tip,
        gas_per_pubdata_byte=transaction.gas_per_pubdata_byte,
        refund_recipient=transaction.refund_recipient,
        options=transaction.options,
    )


def options_from_712(tx: Transaction712) -> TransactionOptions:
    return TransactionOptions(
        chain_id=tx.chain_id,
        nonce=Nonce(tx.nonce),
        gas_limit=tx.gas_limit,
        max_fee_per_gas=tx.maxFeePerGas,
        max_priority_fee_per_gas=tx.maxPriorityFeePerGas,
        gas_price=tx.maxFeePerGas,
    )


def prepare_transaction_options(options: TransactionOptions, from_: HexStr = None):
    opt = {}
    if options.value is not None:
        opt["value"] = options.value

    if (
        options.max_fee_per_gas is not None
        or options.max_priority_fee_per_gas is not None
    ):
        if options.max_priority_fee_per_gas is not None:
            opt["maxPriorityFeePerGas"] = options.max_priority_fee_per_gas
        if options.max_fee_per_gas is not None:
            opt["maxFeePerGas"] = options.max_fee_per_gas
    elif options.gas_price is not None:
        opt["gasPrice"] = options.gas_price

    if options.gas_limit is not None:
        opt["gas"] = options.gas_limit
    if options.nonce is not None:
        opt["nonce"] = options.nonce
    if options.chain_id is not None:
        opt["chainId"] = options.chain_id
    if from_ is not None:
        opt["from"] = from_

    return opt
