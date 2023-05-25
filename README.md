# zkSync2 client sdk

## Contents
- [Getting started](#getting-started)
- [Provider](#provider-zksyncbuilder)
- [Account](#account)
- [Signer](#signer)
- [Transactions](#transactions)
- [Contract interfaces](#contract-interfaces)
- [Examples](#examples)


### Getting started

#### Requirements
| Tool            | Required       |
|-----------------|----------------|
| python          | 3.8, 3.9, 3.10 |
| package manager | pip            |

### how to install

```console
pip install zksync2
```


### Provider (zkSyncBuilder)


#### Design
ZkSync 2.0 is designed with the same styling as web3.<br>
It defines the zksync module based on Ethereum and extends it with zkSync-specific methods.<br>


#### How to construct
For usage, there is `ZkSyncBuilder` that returns a Web3 object with an instance of zksync module.<br>
Construction only needs the URL to the zkSync blockchain.

Example:
```python
from zksync2.module.module_builder import ZkSyncBuilder
...
web3 = ZkSyncBuilder.build("ZKSYNC_NET_URL")
```

#### Module parameters and methods

ZkSync module attributes:

| Attribute | Description                                                     |
|-----------|-----------------------------------------------------------------|
| chain_id  | Returns an integer value for the currently configured "ChainId" |
| gas_price | Returns the current gas price in Wei                            |


ZkSync module methods:

| Method                       | Parameters                              | Return value             | Description                                                                                                                                             |
|------------------------------|-----------------------------------------|--------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| zks_estimate_fee             | zkSync Transaction                      | Fee structure            | Gets Fee for ZkSync transaction                                                                                                                         |
| zks_main_contract            | -                                       | Address of main contract | Return address of main contract                                                                                                                         |
| zks_get_confirmed_tokens     | from, limit                             | List[Token]              | Returns all tokens in the set range by global index                                                                                                     |
| zks_l1_chain_id              | -                                       | ChainID                  | Return ethereum chain ID                                                                                                                                |
| zks_get_all_account_balances | Address                                 | Dict[str, int]           | Return dictionary of token address and its value                                                                                                        |
| zks_get_bridge_contracts     | -                                       | BridgeAddresses          | Returns addresses of all bridge contracts that are interacting with L1 layer                                                                            |
| eth_estimate_gas             | Transaction                             | estimated gas            | Overloaded method of eth_estimate_gas for ZkSync transaction gas estimation                                                                             |
| wait_for_transaction_receipt | Tx Hash, optional timeout,poll_latency  | TxReceipt                | Waits for the transaction to be included into block by its hash and returns its receipt. Optional arguments are `timeout` and `poll_latency` in seconds |
| wait_finalized               | Tx Hash, optional timeout, poll_latency | TxReceipt                | Waits for the transaction to be finalized when finalized block occurs and it's number >= Tx block number                                                |


### Account

Account encapsulate private key and, frequently based on it, the unique user identifier in the network.<br> This unique identifier also mean by wallet address.

#### Account construction

ZkSync2 Python SDK account is compatible with `eth_account` package
In most cases user has its private key and gets account instance by using it.

Example:
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


#### Singer construction

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


#### Methods


Signer has a few methods to generate signature and verify message

| Method            | Parameters                                   | Return value          | Description                                                               |
|-------------------|----------------------------------------------|-----------------------|---------------------------------------------------------------------------|
| sign_typed_data   | EIP712 Structure, optional domain            | Web3 py SignedMessage | Builds `SignedMessage` based on the encoded in EIP712 format Transaction  |
| verify_typed_data | signature, EIP712 structure, optional domain | bool                  | return True if this encoded transaction is signed with provided signature |

Signer class also has the following properties:

| Attribute | Description                                                                    |
|-----------|--------------------------------------------------------------------------------|
| address   | Account address                                                                |
| domain    | domain that is used to generate signature. It's depends on chain_id of network |



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


Methods:

| Method                     | Parameters | Return value | Description                                                      |
|----------------------------|------------|--------------|------------------------------------------------------------------|
| get_account_nonce          | -          | Nonce        | returns account nonce                                            |
| get_deployment_nonce       | -          | Nonce        | return current deployment nonce that is going to be used         |
| increment_deployment_nonce | Address    | Nothing      | Manually increments deployment nonce by provided account address | 


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

Methods:

| Method                     | Parameters                              | Return value | Description                                                                                                                                                                                                                                          |
|----------------------------|-----------------------------------------|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| encode_create              | bytecode, optional `call_data` & `salt` | HexStr       | create binary representation of contract in internal deploying format.<br/> bytecode - contract binary representation, call_data is used for ctor bytecode only, salt is used to generate unique identifier of deploying contract                    |
| encode_create2             | bytecode, optional `call_data` & `salt` | HexStr       | create binary representation of contract in internal deploying format.<br/> bytecode - contract binary representation, call_data is used for ctor bytecode only, salt is used to generate unique identifier of deploying contract                    |
 | compute_l2_create_address  | Address, Nonce                          | Address      | Accepts address of deployer and current deploying nonce and returns address of contract that is going to be deployed by `encode_create` method                                                                                                       |
| compute_l2_create2_address | Address, bytecode, ctor bytecode, salt  | Address      | Accepts address of deployer, binary representation of contract, if needed it's constructor in binary format and self. By default constructor can be b'0' value. Returns address of contract that is going to be deployed by  `encode_create2` method |


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


Methods:

| Method             | Parameters                        | Return value | Description                                                                  |
|--------------------|-----------------------------------|--------------|------------------------------------------------------------------------------|
| encode_method      | function name, function arguments | HexStr       | encode contract function method with it's arguments in binary representation |
| encode_constructor | constructor arguments             | bytes        | encode constructor with arguments in binary representation                   |



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

