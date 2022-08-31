import json
from decimal import Decimal
from unittest import TestCase

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider
from eth_tester import PyEVMBackend
from web3.types import Nonce

from protocol.core.types import Token
from protocol.utility_contracts.contract_deployer import ContractDeployer
from protocol.utility_contracts.l2_eth_bridge import L2ETHBridge
from tests.counter_contract_utils import CounterContractEncoder
from transaction.transaction712 import Transaction712, Transaction712Encoder
from pathlib import Path


def _get_counter_contract_binary() -> bytes:
    p = Path('./counter_contract.hex')
    with p.open(mode='r') as contact_file:
        lines = contact_file.readlines()
        data = "".join(lines)
        return bytes.fromhex(data)


def _get_counter_contract_abi():
    p = Path('./counter_contract_abi.json')
    with p.open(mode='r') as json_f:
        return json.load(json_f)


class TestTransaction712Encode(TestCase):
    ETH_TOKEN = Token.create_eth()
    BRIDGE_ADDRESS = HexStr("0x8c98381FfE6229Ee9E53B6aAb784E86863f61885")
    CONTRACT_RANDOM_ADDRESS = HexStr("0x7e5f4552091a69125d5dfcb7b8c2659029395bdf")
    GAS_LIMIT = 42
    GAS_PRICE = 43
    CHAIN_ID = 270

    ACCOUNT_ADDRESS = "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"

    ENCODE_WITHDRAW_EXPECTED = "71f89a802b2a948c98381ffe6229ee9e53b6aab784e86863f6188580b864d9caed12000000000000000" \
                               "0000000007e5f4552091a69125d5dfcb7b8c2659029395bdf0000000000000000000000000000000000" \
                               "0000000000000000000000000000000000000000000000000000000000000000000000000000000de0b" \
                               "6b3a764000082010e94000000000000000000000000000000000000000080c0c0"

    ENCODE_DEPLOY_EXPECTED = "71f907df802b2a94000000000000000000000000000000000000800" \
                             "680b8c41415dae20000000000000000000000000000000000000000" \
                             "00000000000000000000000000" \
                             "379c09b5568d43b0ac6533a2672ee836815530b412f082f0b2e69915aa50fc" \
                             "00000000000000000000000000000000000000000000000000000000000000" \
                             "0000000000000000000000000000000000000000000000000000000000000000" \
                             "8000000000000000000000000000000000000000000000000000000000000000" \
                             "000000000000000000000000000000000000000000000000000000000000000000" \
                             "82010e940000000000000000000000000000000000000000" \
                             "80f906e3b906e00000002b04000041000000000141016f0000002c040000410000000000140376000000" \
                             "2d010000410000000000210376000000000130004c000000090000613d00a5000a0000034f00a5001f00" \
                             "00034f000000800100003900000040020000390000000000120376000000000100035700000000011000" \
                             "4c0000001d0000c13d0000002d010000410000000001010375000000000110004c000000180000c13d00" \
                             "000080010000390000000002000019000000000300001900a500960000034f0000002001000039000000" \
                             "000010037600000000000103760000002e01000041000000a6000103700000000001000019000000a700" \
                             "01037200010000000000020000008006000039000000400500003900000000006503760000002d010000" \
                             "410000000001010375000000040110008c0000005a0000413d0000002c01000041000000000101037500" \
                             "000000010103770000002f02000041000000000121016f000000300210009c000000440000c13d000000" \
                             "0001000357000000000110004c0000005c0000c13d0000002d0100004100000000010103750000000401" \
                             "10008a000000010200008a0000003203000041000000000221004b000000000200001900000000020320" \
                             "19000000000131016f000000000431013f000000320110009c0000000001000019000000000103401900" \
                             "0000320340009c000000000102c019000000000110004c0000005e0000c13d0000000001000019000000" \
                             "a700010372000000310110009c0000005a0000c13d0000000001000357000000000110004c0000006500" \
                             "00c13d0000002d010000410000000001010375000000040110008a00000032020000410000001f031000" \
                             "8c00000000030000190000000003022019000000000121016f000000000410004c000000000200801900" \
                             "0000320110009c00000000010300190000000001026019000000000110004c000000670000c13d000000" \
                             "0001000019000000a7000103720000000001000019000000a7000103720000000001000019000000a700" \
                             "0103720000000001000019000100000006001d00a5008b0000034f000000010200002900000000001203" \
                             "760000003401000041000000a6000103700000000001000019000000a7000103720000002c0100004100" \
                             "0000000101037500000004011000390000000001010377000100000005001d00a500720000034f000000" \
                             "010100002900000000010103750000003302000041000000000121016f000000a6000103700002000000" \
                             "000002000000010200008a000100000001001d000000000121013f000200000001001d00000000010000" \
                             "1900a5008b0000034f0000000202000029000000000221004b000000820000213d000000010200002900" \
                             "00000001210019000000000200001900a500890000034f0000000200000005000000000001036f000000" \
                             "350100004100000000001003760000001101000039000000040200003900000000001203760000003601" \
                             "000041000000a700010372000000000012035b000000000001036f000000000101035900000000000103" \
                             "6f000000000401037500000000043401cf000000000434022f0000010003300089000000000232022f00" \
                             "000000023201cf000000000242019f0000000000210376000000000001036f0000000504300270000000" \
                             "000540004c0000009e0000613d00000000002103760000002001100039000000010440008a0000000005" \
                             "40004c000000990000c13d0000001f0330018f000000000430004c000000a40000613d00000003033002" \
                             "1000a5008d0000034f000000000001036f000000000001036f000000a500000374000000a60001037000" \
                             "0000a700010372000000000000e001000000000000e001000000000000e001000000000000e001000000" \
                             "0000000000000000000000000000000000000000000000000000ffffff00000000000000000000000000" \
                             "00000000000000000000000000000000ffffe00000000000000000000000000000000000000000000000" \
                             "000000000000ffffc00000000000000000000000000000000000000000000000400000000000000000" \
                             "ffffffff000000000000000000000000000000000000000000000000000000006d4ce63c0000000000" \
                             "00000000000000000000000000000000000000000000007cf5dab00000000000000000000000000000" \
                             "0000000000000000000000000000800000000000000000000000000000000000000000000000000000" \
                             "0000000000000000000000000000000000000000000000000000000000ffffffffffffffff00000000" \
                             "000000000000000000000000000000000000002000000000000000804e487b71000000000000000000" \
                             "0000000000000000000000000000000000000000000000000000000000000000000000000000000000" \
                             "00240000000000000000c0"

    EXECUTE_EXPECTED = "71f859802b2a94e1fab3efd74a77c23b426c302d96372140ff7d0c80a47cf5dab00000000000000000000000000" \
                       "00000000000000000000000000000000000002a82010e94000000000000000000000000000000000000000080c0c0"

    PRIVATE_KEY = b'0' * 31 + b'1'

    def setUp(self) -> None:
        self.account: LocalAccount = Account.from_key(self.PRIVATE_KEY)
        self.web3 = Web3(EthereumTesterProvider(PyEVMBackend()))
        self.l2eth_bridge = L2ETHBridge(contract_address=self.CONTRACT_RANDOM_ADDRESS,
                                        web3=self.web3,
                                        zksync_account=self.account)
        self.ACCOUNT_ADDRESS = Web3.toChecksumAddress(self.ACCOUNT_ADDRESS)
        self.deployer = ContractDeployer(self.web3)
        self.counter_contract_encoder = CounterContractEncoder(self.web3)
        # self.counter_contract_instance = self.web3.eth.contract(abi=_get_counter_contract_abi(),
        #                                                         bytecode=_get_counter_contract_binary())

    def test_encode_withdraw(self):
        # INFO: Can't generate the same address as it under Java SDK for testing, just use it directly
        #       addresses value affects on result
        args = [
            # self.account.address,
            self.ACCOUNT_ADDRESS,
            self.ETH_TOKEN.l2_address,
            self.ETH_TOKEN.to_int(Decimal(1))
        ]
        encoded_function: HexStr = self.l2eth_bridge.contract.encodeABI(fn_name="withdraw", args=args)

        eip_meta: Eip712Meta = {
            "feeToken": self.ETH_TOKEN.l2_address,
            "ergsPerPubdata": 0,
            "ergsPerStorage": 0,
            "factoryDeps": None,
            "aaParams": None
        }
        tx712 = Transaction712(nonce=Nonce(0),
                               gas_price=self.GAS_PRICE,
                               gas_limit=self.GAS_LIMIT,
                               to=self.BRIDGE_ADDRESS,
                               value=0,
                               data=encoded_function,
                               chain_id=self.CHAIN_ID,
                               meta=eip_meta)

        encoded712 = Transaction712Encoder.encode(tx712)
        hex712 = encoded712.hex()
        self.assertEqual(len(self.ENCODE_WITHDRAW_EXPECTED), len(hex712))
        self.assertEqual(self.ENCODE_WITHDRAW_EXPECTED, hex712)

    def test_encode_deploy(self):
        # INFO: function encoding under the Python is different from web3 java
        #       See ContractDeployer
        #       Reason: class ByteStringEncoder(BaseEncoder): for empty bytes generates 32 bytes empty value
        #       meanwhile under Web3 java it's empty array
        #       Under the Solidity engine it must be the same values
        #       but for testing it is different
        #       In the case of invalid processing need to be adapted. See contract deployer

        bytecode = _get_counter_contract_binary()
        call_data = self.deployer.encode_data(bytecode)

        eip_meta: Eip712Meta = {
            "feeToken": self.ETH_TOKEN.l2_address,
            "ergsPerPubdata": 0,
            "ergsPerStorage": 0,
            "factoryDeps": [bytecode],
            "aaParams": None
        }
        tx712 = Transaction712(nonce=Nonce(0),
                               gas_price=self.GAS_PRICE,
                               gas_limit=self.GAS_LIMIT,
                               to=ContractDeployer.DEPLOYER_SYSTEM_CONTRACT_ADDRESS,
                               value=0,
                               data=call_data,
                               chain_id=self.CHAIN_ID,
                               meta=eip_meta)

        encoded712 = Transaction712Encoder.encode(tx712)
        hex712 = encoded712.hex()
        self.assertEqual(len(self.ENCODE_DEPLOY_EXPECTED), len(hex712))
        self.assertEqual(self.ENCODE_DEPLOY_EXPECTED, hex712)

    def test_encode_execute(self):
        # call_data = self.counter_contract_instance.encodeABI(fn_name="increment", args=[42])
        call_data = self.counter_contract_encoder.encode_method("increment", args=[42])
        eip_meta: Eip712Meta = {
            "feeToken": self.ETH_TOKEN.l2_address,
            "ergsPerPubdata": 0,
            "ergsPerStorage": 0,
            "factoryDeps": None,
            "aaParams": None
        }
        tx712 = Transaction712(nonce=Nonce(0),
                               gas_price=self.GAS_PRICE,
                               gas_limit=self.GAS_LIMIT,
                               to="0xe1fab3efd74a77c23b426c302d96372140ff7d0c",
                               value=0,
                               data=call_data,
                               chain_id=self.CHAIN_ID,
                               meta=eip_meta)
        encoded712 = Transaction712Encoder.encode(tx712)
        hex712 = encoded712.hex()
        self.assertEqual(self.EXECUTE_EXPECTED, hex712)
