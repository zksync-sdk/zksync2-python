from typing import Optional

import web3.eth
from web3.types import BlockIdentifier

from zk_types.zk_types import *
from protocol.zksync_module import ZkSync
from crypto.eth_signer import EthSignerBase
from web3.eth import Eth

# from eth_abi import EI
# from eth_abi.abi import EIP20_ABI
from web3.contract import ContractEvent, ContractFunction
# from web3_wrapped_contract


class ZkSyncWallet:

    def __init__(self, module: ZkSync, signer: EthSignerBase):
        self.zksync = module
        self.signer = signer

    # INFO: might be static method
    def get_balance(self, address: Optional[Address] = None, token: Optional[Token] = None,
                    block_param: Optional[BlockIdentifier] = None):
        param_token = token
        param_block_param = block_param
        param_address = address
        if param_address is None:
            param_address = self.signer.get_address()
        if param_block_param is None:
            param_block_param = "committed"
        if param_token is None:
            param_token = Token.create_eth()
        return self.zksync.eth_get_balance(param_address, param_block_param, param_token.address)

    def get_nonce(self, block_param: Optional[BlockIdentifier] = "latest"):
        param_address = self.signer.get_address()
        return self.zksync.get_transaction_count(param_address, block_param)

    def transfer(self, transfer: Transfer):
        if transfer.nonce is None:
            transfer.nonce = self.get_nonce()
        if transfer.token is None:
            transfer.token = Token.create_eth()
        # TODO: add implementation based on predefined contract here

    def withdraw(self, withdraw: Withdraw):
        pass

    def deploy(self, bytecode: bytes, calldata: bytes = None, nonce: int = None):
        pass

    def _estimate_and_send(self):
        pass
