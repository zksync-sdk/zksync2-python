import json

from eth_typing import HexStr
from web3 import Web3
from web3.contract import Contract
from pathlib import Path
# from contract_base import ContractBase
from eth_account.signers.base import BaseAccount

from protocol.contract_base import ContractBase

zksync_abi_cache = None
zksync_default_path = Path('./contract_abi/ZkSync.json')


# def build_zksync_contract(w3: Web3, contract_address, abi=None) -> 'Contract':
#     global zksync_abi_cache
#
#     if abi is not None:
#         return w3.eth.contract(address=contract_address, abi=abi)
#
#     if zksync_abi_cache is None:
#         with zksync_default_path.open(mode='r') as json_file:
#             data = json.load(json_file)
#             zksync_abi_cache = data['abi']
#     return w3.eth.contract(address=contract_address, abi=zksync_abi_cache)

def _zksync_abi_default():
    global zksync_abi_cache

    if zksync_abi_cache is None:
        with zksync_default_path.open(mode='r') as json_file:
            data = json.load(json_file)
            zksync_abi_cache = data['abi']
    return zksync_abi_cache


class ZkSyncContract(ContractBase):

    def __init__(self, zksync_main_contract: HexStr, web3: Web3, account: BaseAccount):
        super().__init__(zksync_main_contract, web3, account, _zksync_abi_default())

    def activate_priority_mode(self, eth_expiration_block: int):
        return self._call_method('activatePriorityMode', eth_expiration_block)

    def add_custom_token(self, _token: str, _name: str, _symbol: str, _decimals: int, _queue_type: int, _op_tree: int):
        return self._call_method('addCustomToken', _token, _name, _symbol, _decimals, _queue_type, _op_tree)

    def add_token(self, _token: str, _queue_type: int, _op_tree: int):
        return self._call_method('addToken', _token, _queue_type, _op_tree)

    def add_token_base_cost(self, _gas_price: int, _queue_type: int, _op_tree: int):
        return self._call_method('addTokenBaseCost', _gas_price, _queue_type, _op_tree)

    def approve_emergency_diamond_cut_as_security_council_member(self, _diamond_cut_hash: bytes):
        return self._call_method('approveEmergencyDiamondCutAsSecurityCouncilMember', _diamond_cut_hash)

    def cancel_diamond_cut_proposal(self):
        return self._call_method('cancelDiamondCutProposal')

    def change_governor(self, _new_governor: str):
        return self._call_method('changeGovernor', _new_governor)

    def deploy_contract_base_cost(self, _gas_price: int,
                                  _ergs_limit: int,
                                  _bytecode_length: int,
                                  _calldata_length: int,
                                  _queue_type: int,
                                  _op_tree: int):
        return self._call_method('deployContractBaseCost',
                                 _gas_price,
                                 _ergs_limit,
                                 _bytecode_length,
                                 _calldata_length,
                                 _queue_type,
                                 _op_tree)

    def deposit_base_cost(self, _gas_price: int, _queue_type: int, _op_tree: int):
        return self._call_method('depositBaseCost', _gas_price, _queue_type, _op_tree)

    def deposit_erc20(self, _token: str, _amount: int, _zk_sync_address: str, _queue_type: int, _op_tree: int):
        return self._call_method('depositERC20', _token, _amount, _zk_sync_address, _queue_type, _op_tree)

    def deposit_eth(self, _amount: int, _zk_sync_address: str, _queue_type: int, _op_tree: int, _value: int):
        return self._call_method('depositETH', _amount, _zk_sync_address, _queue_type, _op_tree, _value)

    def emergency_freeze_diamond(self):
        return self._call_method('emergencyFreezeDiamond')

    def execute_base_cost(self, _gas_price: int,
                          _ergs_limit: int,
                          _calldata_length: int,
                          _queue_type: int,
                          _op_tree: int):
        return self._call_method('executeBaseCost', _gas_price, _ergs_limit, _calldata_length, _queue_type, _op_tree)

    def get_governor(self):
        return self._call_method('getGovernor')

    def get_pending_balance(self, _address: str, _token: str):
        return self._call_method('getPendingBalance', _address, _token)

    def get_total_blocks_committed(self):
        return self._call_method('getTotalBlocksCommitted')

    def get_total_blocks_executed(self):
        return self._call_method('getTotalBlocksExecuted')

    def get_total_blocks_verified(self):
        return self._call_method('getTotalBlocksVerified')

    def get_total_priority_requests(self):
        return self._call_method('getTotalPriorityRequests')

    def get_verifier(self):
        return self._call_method('getVerifier')

    def is_validator(self, _address: str):
        return self._call_method('isValidator', _address)

    def move_priority_ops_from_buffer_to_main_queue(self, _n_ops_to_move: int, _op_tree: int):
        return self._call_method('movePriorityOpsFromBufferToMainQueue', _n_ops_to_move, _op_tree)

    def place_bid_for_blocks_processing_auction(self, _complexity_root: int, _op_tree: int):
        return self._call_method('placeBidForBlocksProcessingAuction', _complexity_root, _op_tree)

    def request_deploy_contract(self, _bytecode: bytes,
                                _calldata: bytes,
                                _ergs_limit: int,
                                _queue_type: int,
                                _op_tree: int):
        return self._call_method('requestDeployContract', _bytecode, _calldata, _ergs_limit, _queue_type, _op_tree)

    def request_execute(self,
                        _contract_address_L2: str,
                        _calldata: bytes,
                        _ergs_limit: int,
                        _queue_type: int,
                        _op_tree: int):
        return self._call_method('requestExecute', _contract_address_L2, _calldata, _ergs_limit, _queue_type, _op_tree)

    def request_withdraw(self, _token: str, _amount: int, _to: str, _queue_type: int, _op_tree: int):
        return self._call_method('requestWithdraw', _token, _amount, _to, _queue_type, _op_tree)

    def revert_blocks(self, _blocks_to_revert: int):
        return self._call_method('revertBlocks', _blocks_to_revert)

    def set_validator(self, _validator: str, _active: bool):
        return self._call_method('setValidator', _validator, _active)

    def unfreeze_diamond(self):
        return self._call_method('unfreezeDiamond')

    def update_priority_mode_sub_epoch(self):
        return self._call_method('updatePriorityModeSubEpoch')

    def withdraw_base_cost(self, _gas_price: int, _queue_type: int, _op_tree: int):
        return self._call_method('withdrawBaseCost', _gas_price, _queue_type, _op_tree)

    def withdraw_pending_balance(self, _owner: str, _token: str, _amount: int):
        return self._call_method('withdrawPendingBalance', _owner, _token, _amount)
