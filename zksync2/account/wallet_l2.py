from typing import Union, List

from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt, BlockIdentifier
from web3._utils.contracts import encode_abi

from eth_typing import HexStr, Address
from eth_utils import event_signature_to_log_topic, add_0x_prefix
from eth_account import Account
from eth_account.signers.base import BaseAccount
from eth_abi import abi

from zksync2.core.types import BridgeAddresses, Token, ZksMessageProof, EthBlockParams, TransactionDetails, \
    DepositTransaction, ADDRESS_DEFAULT, ZkBlockParams, L2BridgeContracts, TransferTransaction
from zksync2.core.utils import RecommendedGasLimit, to_bytes, is_eth, apply_l1_to_l2_alias, \
    get_custom_bridge_data, BOOTLOADER_FORMAL_ADDRESS, undo_l1_to_l2_alias
from zksync2.manage_contracts.deploy_addresses import ZkSyncAddresses
from zksync2.manage_contracts.erc20_contract import get_erc20_abi
from zksync2.manage_contracts.l1_bridge import L1Bridge
from zksync2.manage_contracts.l2_bridge import _l2_bridge_abi_default
from zksync2.manage_contracts.nonce_holder import NonceHolder, _nonce_holder_abi_default
from zksync2.manage_contracts.zksync_contract import ZkSyncContract
from zksync2.module.request_types import Transaction
from zksync2.module.response_types import ZksAccountBalances
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction712 import Transaction712
from zksync2.transaction.transaction_builders import TxFunctionCall, TxWithdraw


class WalletL2:
    def __init__(self,
                 zksync_web3: Web3,
                 eth_web3: Web3,
                 l1_account: BaseAccount):
        self._eth_web3 = eth_web3
        self._zksync_web3 = zksync_web3
        self._main_contract_address = self._zksync_web3.zksync.zks_main_contract()
        self._l1_account = l1_account
        self._main_contract = ZkSyncContract(zksync_main_contract=self._main_contract_address,
                                             eth=self._eth_web3,
                                             account=l1_account)
        bridge_addresses: BridgeAddresses = self._zksync_web3.zksync.zks_get_bridge_contracts()
        self._l1_bridge = L1Bridge(bridge_addresses.erc20_l1_default_bridge,
                                   self._eth_web3, l1_account)

    def get_balance(self, block_tag = ZkBlockParams.COMMITTED.value, token_address: HexStr = None) -> int:
        return self._zksync_web3.zksync.zks_get_balance(self._l1_account.address, block_tag, token_address)

    def get_all_balances(self) -> ZksAccountBalances:
        return self._zksync_web3.zksync.zks_get_all_account_balances(self._l1_account.address)

    def get_deployment_nonce(self) -> int:
        nonce_holder = self._zksync_web3.zksync.contract(address=ZkSyncAddresses.NONCE_HOLDER_ADDRESS.value,
                                                         abi=_nonce_holder_abi_default())
        deployment_nonce = nonce_holder.functions.getDeploymentNonce(self._l1_account.address).call(
            {
                "from": self._l1_account.address
            })
        return deployment_nonce

    def get_l2_bridge_contracts(self) -> L2BridgeContracts:
        addresses = self._zksync_web3.zksync.zks_get_bridge_contracts()
        return L2BridgeContracts(erc20=self._zksync_web3.eth.contract(address=Web3.to_checksum_address(addresses.erc20_l2_default_bridge),
                                                                      abi=_l2_bridge_abi_default()),
                                 weth=self._zksync_web3.eth.contract(address=Web3.to_checksum_address(addresses.weth_bridge_l2),
                                                                     abi=_l2_bridge_abi_default()))

    def transfer(self, tx: TransferTransaction) -> HexStr:
        if tx.chain_id is None:
            tx.chain_id = self._zksync_web3.zksync.chain_id

        if tx.nonce is None:
            tx.nonce = self._zksync_web3.zksync.get_transaction_count(self._l1_account.address, ZkBlockParams.LATEST.value)
        if tx.gas_price == 0:
            tx.gas_price = self._zksync_web3.zksync.gas_price

        if tx.token_address is None or is_eth(tx.token_address):
            transaction = TxFunctionCall(
                chain_id=tx.chain_id,
                nonce=tx.nonce,
                from_=self._l1_account.address,
                to=tx.to,
                value=self._zksync_web3.to_wei(tx.amount, "ether"),
                gas_limit=0,
                gas_price=tx.gas_price
            )

            estimate_gas = self._zksync_web3.zksync.eth_estimate_gas(transaction.tx)
            tx_712 = transaction.tx712(estimate_gas)
            signer = PrivateKeyEthSigner(self._l1_account, tx.chain_id)
            signed_message = signer.sign_typed_data(tx_712.to_eip712_struct())

            msg = tx_712.encode(signed_message)
            tx_hash = self._zksync_web3.zksync.send_raw_transaction(msg)

            return tx_hash
        else:
            token_contract = self._zksync_web3.zksync.contract(tx.token_address, abi=get_erc20_abi())
            tx = token_contract.functions.transfer(tx.to, tx.amount).build_transaction({
                "nonce": tx.nonce,
                "from": self._l1_account.address,
                "maxPriorityFeePerGas": 1_000_000,
                "maxFeePerGas": tx.gas_price,
            })

            signed = self._l1_account.sign_transaction(tx)
            tx_hash = self._zksync_web3.zksync.send_raw_transaction(signed.rawTransaction)

            return tx_hash

    def withdraw(self,
                 token: HexStr,
                 amount: int,
                 to: HexStr = None,
                 bridge_address: HexStr = None):

        if is_eth(token):
            withdrawal = TxWithdraw(
                web3=self._zksync_web3,
                token=token,
                amount=amount,
                gas_limit=0,  # unknown
                account=self._l1_account,
                to=to,
                bridge_address=bridge_address
            )

            estimated_gas = self._zksync_web3.zksync.eth_estimate_gas(withdrawal.tx)
            tx = withdrawal.estimated_gas(estimated_gas)
            signed = self._l1_account.sign_transaction(tx)

            return self._zksync_web3.zksync.send_raw_transaction(signed.rawTransaction)

        if bridge_address is not None:
            bridge = self._zksync_web3.zksync.contract(address=Web3.to_checksum_address(bridge_address),
                                                       abi=_l2_bridge_abi_default())
        else:
            bridge = self.get_l2_bridge_contracts().erc20

        tx = bridge.functions.withdraw(self._l1_account.address,
                                       token,
                                       amount).build_transaction(
            {
                "from": self._l1_account.address,
                "nonce": self._zksync_web3.zksync.get_transaction_count(self._l1_account.address)
            })

        signed_tx = self._l1_account.sign_transaction(tx)
        return self._zksync_web3.zksync.send_raw_transaction(signed_tx.rawTransaction)

