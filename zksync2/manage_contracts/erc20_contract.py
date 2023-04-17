import json
import importlib.resources as pkg_resources
from typing import Optional
from eth_typing import HexStr, HexAddress
from web3 import Web3
from web3.types import TxReceipt
from zksync2.manage_contracts.contract_encoder_base import BaseContractEncoder
from zksync2.manage_contracts import contract_abi
from eth_account.signers.local import LocalAccount


erc_20_abi_cache = None


def _erc_20_abi_default():
    global erc_20_abi_cache

    if erc_20_abi_cache is None:
        with pkg_resources.path(contract_abi, "IERC20.json") as p:
            with p.open(mode="r") as json_file:
                data = json.load(json_file)
                erc_20_abi_cache = data["abi"]
    return erc_20_abi_cache


class ERC20Contract:
    """
    Interact with ERC-20 Contract
    """

    MAX_ERC20_APPROVE_AMOUNT = 2 ^ 256 - 1
    ERC20_APPROVE_THRESHOLD = 2 ^ 255

    def __init__(self, web3: Web3, contract_address: HexStr, abi):
        self.web3 = web3
        self.contract_address = contract_address
        self.abi = abi
        self.contract = self.web3.contract(self.contract_address, abi=self.abi)


class ERC20ContractRead(ERC20Contract):
    """
    Read ERC-20 Contract information
    """

    def name(self) -> str:
        return self.contract.functions.name().call(
            {
                "chainId": self.web3.chain_id,
            }
        )

    def total_supply(self) -> int:
        return self.contract.functions.totalSupply().call(
            {
                "chainId": self.web3.chain_id,
            }
        )

    def decimals(self) -> int:
        return self.contract.functions.decimals().call(
            {
                "chainId": self.web3.chain_id,
            }
        )

    def balance_of(self, addr: HexStr) -> int:
        return self.contract.functions.balanceOf(addr).call()

    def symbol(self) -> str:
        return self.contract.functions.symbol().call(
            {
                "chainId": self.web3.chain_id,
            }
        )

    def allowance(self, owner: HexStr, sender: HexStr) -> int:
        return self.contract.functions.allowance(owner, sender).call(
            {
                "chainId": self.web3.chain_id,
            }
        )


class ERC20ContractWrite(ERC20Contract):
    """
    Make actions within ERC-20 Contract
    """

    def __init__(
        self, account: LocalAccount, web3: Web3, contract_address: HexAddress, abi
    ):
        self.account = account
        super().__init__(web3, contract_address, abi)

    def _nonce(self) -> int:
        return self.module.get_transaction_count(self.account.address)

    def approve(self, zksync_address: HexStr, amount, gas_limit: int) -> TxReceipt:
        nonce = self._nonce()
        gas_price = self.module.gas_price
        tx = self.contract.functions.approve(zksync_address, amount).build_transaction(
            {
                "chainId": self.module.chain_id,
                "from": self.account.address,
                "gasPrice": gas_price,
                "gas": gas_limit,
                "nonce": nonce,
            }
        )
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.module.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.module.wait_for_transaction_receipt(tx_hash)
        return tx_receipt

    def transfer(self, _to: str, _value: int):
        return self.contract.functions.transfer(_to, _value).call(
            {
                "chainId": self.web3.chain_id, 
                "from": self.account.address
            }
        )


class ERC20Encoder(BaseContractEncoder):
    def __init__(self, web3: Web3, abi: Optional[dict] = None):
        if abi is None:
            abi = _erc_20_abi_default()
        super(ERC20Encoder, self).__init__(web3, abi)
