import os
from decimal import Decimal

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr, HexAddress

from zksync2.core.types import ZkBlockParams
from zksync2.manage_contracts.erc20_contract import ERC20ContractRead, ERC20Encoder, _erc_20_abi_default
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction_builders import TxFunctionCall


# Byte-format private key
PRIVATE_KEY = bytes.fromhex(os.environ.get("PRIVATE_KEY"))


def get_erc20_balance(
    zk_web3: ZkSyncBuilder,
    address: HexAddress,
    contract_address: HexAddress,
    abi
) -> float:
    """
    Get ERC20 balance of ETH address on zkSync network

    :param zk_web3:
        Instance of ZkSyncBuilder that interacts with zkSync network

    :param address:
        ETH address that you want to get ERC-20 balance of.

    :param contract_address:
        ETH address that you want to get ERC-20 balance of.

    :return:
        ERC20 formated balance of the requested address
    """

    # Get readable contract instance
    contract = ERC20ContractRead(
        web3=zk_web3.zksync, contract_address=contract_address, abi=abi
    )

    # Get decimals of the contract
    contract_decimals = contract.decimals()

    # Query contract's balance
    erc20_balance = contract.balance_of(address)

    # Return Formated Balance
    return float(Decimal(erc20_balance) / Decimal(10) ** contract_decimals)


def transfer_erc20(
    zk_web3: ZkSyncBuilder,
    account: LocalAccount,
    to: HexAddress,
    contract_address: HexAddress,
    amount: int,
) -> HexStr:
    """
    Transfer ERC20 token to a specific address on zkSync network

    :param zk_web3:
        Instance of ZkSyncBuilder that interacts with zkSync network.

    :param account:
        From which account the transfer will be made.

    :param to:
        ETH address that you want to transfer tokens to.

    :param contract_address:
        ERC-20 contract address that the transfer will be made within.

    :param amount:
        ERC-20 token amount to be sent.

    :return:
        The transaction hash of the deposit transaction.
    """

    # Get chain id of zkSync network
    chain_id = zk_web3.zksync.chain_id

    # Signer is used to generate signature of provided transaction
    signer = PrivateKeyEthSigner(account, chain_id)

    # Get current gas price in Wei
    gas_price = zk_web3.zksync.gas_price

    # Get nonce of ETH address on zkSync network
    nonce = zk_web3.zksync.get_transaction_count(
        account.address, ZkBlockParams.COMMITTED.value
    )

    erc20_encoder = ERC20Encoder(zk_web3)

    # Transfer parameters
    transfer_params = (to, amount)

    # Encode arguments
    call_data = erc20_encoder.encode_method("transfer", args=transfer_params)

    # Create transaction
    func_call = TxFunctionCall(
        chain_id=chain_id,
        nonce=nonce,
        from_=account.address,
        to=contract_address,
        data=call_data,
        gas_limit=0,  # UNKNOWN AT THIS STATE
        gas_price=gas_price,
        max_priority_fee_per_gas=100000000,
    )

    # ZkSync transaction gas estimation
    estimate_gas = zk_web3.zksync.eth_estimate_gas(func_call.tx)
    print(f"Fee for transaction is: {estimate_gas * gas_price}")

    # Convert transaction to EIP-712 format
    tx_712 = func_call.tx712(estimated_gas=estimate_gas)
    print(f"Tx 712 : {tx_712}")

    # Sign message & encode it
    signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
    print(f"Signed tx 712 : {signed_message}")

    # Encode signed message
    msg = tx_712.encode(signed_message)
    print(f"Msg  : {msg}")

    # Transfer ERC-20 token
    tx_hash = zk_web3.zksync.send_raw_transaction(msg)

    # Wait for transaction to be included in a block
    tx_receipt = zk_web3.zksync.wait_for_transaction_receipt(
        tx_hash, timeout=240, poll_latency=0.5
    )
    print(f"Tx status: {tx_receipt['status']}")
    print(f"Tx hash: {tx_receipt['transactionHash'].hex()}")


if __name__ == "__main__":
    # Some ERC20 Address
    SERC20_Address = "0xd782e03F4818A7eDb0bc5f70748F67B4e59CdB33"

    # Connect to zkSync provider
    zk_web3 = ZkSyncBuilder.build("https://zksync2-testnet.zksync.dev")

    # Get account object by providing byte-format private key
    account: LocalAccount = Account.from_key(PRIVATE_KEY)

    print(
        f"ERC-20 Balance before transfer : {get_erc20_balance(zk_web3=zk_web3, address=account.address, contract_address=SERC20_Address, abi=_erc_20_abi_default())}"
    )

    # Perform ERC-20 transfer
    transfer_erc20(
        zk_web3=zk_web3,
        account=account,
        to="0xB8301fB6C3948C23D21ba68e1bD355F87168Bbe8",
        contract_address=SERC20_Address,
        amount=1,
    )

    print(
        f"ERC-20 Balance after transfer : {get_erc20_balance(zk_web3=zk_web3, address=account.address, contract_address=SERC20_Address, abi=_erc_20_abi_default())}"
    )
