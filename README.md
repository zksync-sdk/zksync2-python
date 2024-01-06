# 🚀 zksync2-python Python SDK 🚀

![Era Logo](https://github.com/matter-labs/era-contracts/raw/main/eraLogo.svg)

In order to provide easy access to all the features of zkSync Era, the `zksync2-python` Python SDK was created,
which is made in a way that has an interface very similar to those of [web3py](https://web3py.readthedocs.io/en/v6.6.1/). In
fact, `web3py` is a peer dependency of our library and most of the objects exported by `zksync2-python` inherit from the corresponding `web3py` objects and override only the fields that need
to be changed.

While most of the existing SDKs functionalities should work out of the box, deploying smart contracts or using unique zkSync features,
like account abstraction, requires providing additional fields to those that Ethereum transactions have by default.

The library is made in such a way that after replacing `web3py` with `zksync2-python` most client apps will work out of
box.

🔗 For a detailed walkthrough, refer to the [official documentation](https://era.zksync.io/docs/api/python).

## 📌 Overview

To begin, it is useful to have a basic understanding of the types of objects available and what they are responsible for, at a high level:

-   `Provider` provides connection to the zkSync Era blockchain, which allows querying the blockchain state, such as account, block or transaction details,
    querying event logs or evaluating read-only code using call. Additionally, the client facilitates writing to the blockchain by sending
    transactions.
-   `Wallet` wraps all operations that interact with an account. An account generally has a private key, which can be used to sign a variety of
    types of payloads. It provides easy usage of the most common features.

## 🛠 Prerequisites
| Tool            | Required       |
|-----------------|----------------|
| python          | 3.8, 3.9, 3.10 |
| package manager | pip            |

## 📥 Installation & Setup

```console
pip install zksync2
```


### Connect to the zkSync Era network:

```python
from zksync2.module.module_builder import ZkSyncBuilder
...
web3 = ZkSyncBuilder.build("ZKSYNC_NET_URL")
```

### Account

Account encapsulate private key and, frequently based on it, the unique user identifier in the network.<br> This unique identifier also mean by wallet address.

#### Account construction

ZkSync2 Python SDK account is compatible with `eth_account` package
In most cases user has its private key and gets account instance by using it.

```python
from eth_account import Account
from eth_account.signers.local import LocalAccount
...
account: LocalAccount = Account.from_key("PRIVATE_KEY")

```

The base property that is used directly of account is: `Account.address`


### Signer

Signer is used to generate signature of provided transaction based on your account(your private key)<br>
This signature is added to the final EIP712 transaction for its validation


#### Signer construction

zkSync2 already has implementation of signer. For constructing the instance it needs only account and chain_id

Example:

```python
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from eth_account import Account
from zksync2.module.module_builder import ZkSyncBuilder


account = Account.from_key("PRIVATE_KEY")
zksync_web3 = ZkSyncBuilder.build("ZKSYNC_NETWORK_URL")
...
chain_id = zksync_web3.zksync.chain_id
signer = PrivateKeyEthSigner(account, chain_id)
```

### Transactions

Basic type of ZkSync transaction is quite similar to the Web3 based one<br>
It's defined in the package: zksync2.module.request_type<br>

But for sending and signed transaction it's necessary to sign and encode it in EIP712 structure<br>
EIP712 transaction type can be found in package: zksync2.transaction.transaction712
There are transaction builders in assistance for<br>
convert ordinary transaction to EIP712 :

* TxFunctionCall
* TxCreateContract
* TxCreate2Contract
* TxWithdraw

Usage will be described in the examples [section][#Examples]


### Contract interfaces

There is a set of system contract that helps execute and interact with ZkSync2 network<br>
For user needs there are the following contracts:

* ZkSyncContract
* L1Bridge
* L2Bridge
* NonceHolder
* ERC20Encoder
* PrecomputeContractDeployer
* ContractEncoder
* PaymasterFlowEncoder



### ZkSyncContract

ZkSyncContract is the implementation of ZkSync main contract functionality.<br>
It's deployed on the L1 network and used like a bridge for providing functionality between L1 and L2<br>
For instance, it handles things relate to the withdrawal operation

To construct object it needs contract main address, L1 Web3 instance and L1 account<br>
Example:

```python

from web3 import Web3
from zksync2.manage_contracts.zksync_contract import ZkSyncContract
from zksync2.module.module_builder import ZkSyncBuilder
from eth_account import Account
from eth_account.signers.local import LocalAccount

zksync = ZkSyncBuilder.build('URL_TO_ZKSYNC_NETWORK')
eth_web3 = Web3(Web3.HTTPProvider('URL_TO_ETH_NETWORK'))
account: LocalAccount = Account.from_key('YOUR_PRIVATE_KEY')
zksync_contract = ZkSyncContract(zksync.zksync.zks_main_contract(),
                                      eth_web3,
                                      account)
```


#### NonceHolder

`NonceHolder` contract is handling the deployment nonce <br>
It's useful to precompute address for contract that is going to be deployer in the network.<br>
To construct it there are need only `account` and `Web3` object with integrated zksync module

```python
from zksync2.manage_contracts.nonce_holder import NonceHolder
from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.module.module_builder import ZkSyncBuilder

zksync_web3 = ZkSyncBuilder.build("ZKSYNC_NETWORK_URL")
account: LocalAccount = Account.from_key("PRIVATE_KEY")
nonce_holder = NonceHolder(zksync_web3, account)
```

#### ERC20Encoder

This is the helper for encoding ERC20 methods. It's used for transfer non-native tokens<br>

Construction needs only Web3 object with appended zksync module(ZkSyncBuilder)

It has only 1 single method: `encode_method` with arguments of function name, and it's args
Usage example you may find in [section](#examples) `Transfer funds (ERC20 tokens)`   


#### PrecomputeContractDeployer

PrecomputeContractDeployer is utility contract represented as type to cover the following functionality:

* encode binary contract representation by `create` method for further deploying
* encode binary contract representation by `create2` method for further deploying
* Precompute contract address for `create` and `create2` methods

Construction: needs only web3 object with appended zksync module


Example:

```python
from zksync2.manage_contracts.precompute_contract_deployer import PrecomputeContractDeployer
from zksync2.module.module_builder import ZkSyncBuilder

zksync_web3 = ZkSyncBuilder.build("ZKSYNC_NETWORK_URL")
deployer = PrecomputeContractDeployer(zksync_web3)
```

The most functionality is hidden in the function builder helper types. See transaction [section](#transactions)  

### ContractEncoder

This is type that helps with encoding contract methods and constructor <br>
that are used as the data for transaction building

Example of construction:

```python
from pathlib import Path
from zksync2.manage_contracts.contract_encoder_base import ContractEncoder
from zksync2.module.module_builder import ZkSyncBuilder

zksync_web3 = ZkSyncBuilder.build('ZKSYNC_TEST_URL')
counter_contract = ContractEncoder.from_json(zksync_web3, Path("./Counter.json"))
```

#### PaymasterFlowEncoder

PaymasterFlowEncoder is utility contract for encoding Paymaster parameters.<br>
Construction contract needs only Web3 Module object. It can be Eth or ZkSync.<br>

Example:
```python
from zksync2.manage_contracts.paymaster_utils import PaymasterFlowEncoder
from zksync2.module.module_builder import ZkSyncBuilder

zksync_web3 = ZkSyncBuilder.build("ZKSYNC_NETWORK_URL")
paymaster_encoder = PaymasterFlowEncoder(zksync_web3)
```

This utility contract has 2 methods wrapped directly to python:

* encode_approval_based
* encode_general

For example and usage, please have a look into example [section](#examples)


### Examples

* [check balance](./examples/11_check_balance.py)
* [deposit funds](./examples/01_deposit.py)
* [transfer](./examples/02_transfer.py)
* [transfer erc20 tokens](./examples/03_transfer_erc20_token.py)
* [withdraw funds](./examples/09_withdrawal.py)
* [finalize withdrawal](./examples/10_finalize_withdrawal.py)
* [deploy contract, precompute address by create](./examples/04_deploy_create.py)
* [deploy contract with constructor(create method) and interact with contract](./examples/05_deploy_create_with_constructor.py)
* [deploy contract with dependent contract(create method)](./examples/06_deploy_create_with_deps.py)
* [deploy contract, precompute address by create2](./examples/07_deploy_create2.py)
* [deploy contract with dependency, precompute address by create2](./examples/08_deploy_create2_deps.py)
* [how to compile solidity contracts](./examples/README.md)

