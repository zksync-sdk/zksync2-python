import string

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from web3 import Web3

from zksync2.core.types import EthBlockParams
from zksync2.core.utils import DEFAULT_GAS_PER_PUBDATA_LIMIT
from zksync2.module.request_types import EIP712Meta
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction712 import Transaction712
from zksync2.transaction.transaction_builders import TxBase


def sign_payload_with_ecdsa(payload: bytes, secret, provider: Web3) -> string:
    account: LocalAccount = Account.from_key(secret)
    signer = PrivateKeyEthSigner(account, provider.eth.chain_id)

    return signer.sign_message(payload).signature


def sign_payload_with_multiple_ecdsa(payload: bytes, secrets: [str], provider):
    signatures = []
    for secret in secrets:
        account: LocalAccount = Account.from_key(secret)
        signer = PrivateKeyEthSigner(account, provider.eth.chain_id)
        signatures.append(signer.sign_message(payload).signature)
    return b"".join(signatures)


def populate_transaction_ecdsa(
    tx: TxBase, from_: str, secret: str, provider: Web3
) -> Transaction712:
    if provider is None:
        raise ValueError(f"Must be True or False. Got: {provider}")

    tx.tx["chainId"] = provider.eth.chain_id
    tx.tx["gas"] = tx.tx["gas"] or 0
    tx.tx["value"] = tx.tx["value"] or 0
    tx.tx["data"] = tx.tx["data"] or 0
    tx.tx["eip712Meta"] = tx.tx["eip712Meta"] or EIP712Meta()
    tx.tx["eip712Meta"].gas_per_pub_data = (
        DEFAULT_GAS_PER_PUBDATA_LIMIT
        if tx.tx["eip712Meta"].gas_per_pub_data is None
        else tx.tx["eip712Meta"].gas_per_pub_data
    )
    tx.tx["eip712Meta"].factory_deps = (
        []
        if tx.tx["eip712Meta"].factory_deps is None
        else tx.tx["eip712Meta"].factory_deps
    )

    fee = None
    if from_ is not None:
        is_contract_address = (
            len(provider.eth.get_code(Web3.to_checksum_address(from_))) != 0
        )
        if is_contract_address:
            # Gas estimation does not work when initiator is contract account (works only with EOA).
            # In order to estimation gas, the transaction's from value is replaced with signer's address.
            fee = provider.zksync.zks_estimate_fee(
                {
                    **tx.tx712(0).to_zk_transaction(),
                    "from": Account.from_key(secret).address,
                }
            )

    tx.tx["from"] = Account.from_key(secret).address if from_ is None else from_
    tx.tx["nonce"] = tx.tx["nonce"] or provider.zksync.get_transaction_count(
        Web3.to_checksum_address(tx.tx["from"]), EthBlockParams.PENDING.value
    )
    if fee is None:
        fee = provider.zksync.zks_estimate_fee(tx.tx712(0).to_zk_transaction())
    gas_limit = tx.tx["gas"] or fee.gas_limit
    tx.tx["maxFeePerGas"] = tx.tx["maxFeePerGas"] or fee.max_fee_per_gas
    tx.tx["maxPriorityFeePerGas"] = (
        tx.tx["maxPriorityFeePerGas"] or fee.max_priority_fee_per_gas
    )

    return tx.tx712(gas_limit)


def populate_transaction_multiple_ecdsa(
    tx: TxBase, from_: str, secret: [HexStr], provider: Web3
) -> Transaction712:
    return populate_transaction_ecdsa(tx, from_, secret[0], provider)
