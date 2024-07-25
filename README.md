# 🚀 zksync2 Python SDK 🚀

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-orange)](LICENSE-APACHE)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](https://www.contributor-covenant.org/)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-orange)](.github/CONTRIBUTING.md)
[![X (formerly Twitter) Follow](https://badgen.net/badge/twitter/@zksyncDevs/1DA1F2?icon&label)](https://x.com/zksyncDevs)
[![Code Style: Google](https://img.shields.io/badge/code%20style-google-blueviolet.svg)](https://github.com/google/gts)

[![ZKsync Era Logo](logo.svg)](https://zksync.io/)

In order to provide easy access to all the features of ZKsync Era, the `zksync2` Python SDK was created,
which is made in a way that has an interface very similar to those of [web3.py](https://web3py.readthedocs.io/en/v6.6.1/). In
fact, `web3.py` is a peer dependency of our library and most of the objects exported by `zksync2` inherit from the corresponding `web3.py` objects and override only the fields that need
to be changed.

While most of the existing SDKs functionalities should work out of the box, deploying smart contracts or using unique ZKsync Era features,
like account abstraction, requires providing additional fields to those that Ethereum transactions have by default.

The library is made in such a way that after replacing `web3.py` with `zksync2` most client apps will work out of
box.

🔗 For a detailed walkthrough, refer to the [official documentation](https://docs.zksync.io/sdk/python/getting-started).

## 📌 Overview

To begin, it is useful to have a basic understanding of the types of objects available and what they are responsible for, at a high level:

-   `Provider` provides connection to the ZKsync Era blockchain, which allows querying the blockchain state, such as account, block or transaction details,
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
## 📝 Examples

The complete examples with various use cases are available [here](https://github.com/zksync-sdk/zksync2-examples/tree/main/python).

### Connect to the ZKsync Era network:

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

### Create a wallet

```python
PRIVATE_KEY = HexStr("<PRIATE_KEY>")
account: LocalAccount = Account.from_key(env_key.key)
wallet = Wallet(zk_sync, eth_web3, account)
```

### Check account balances

```python
eth_balance = wallet.getBalance() # balance on ZKsync Era network

eth_balance_l1 = wallet.getBalanceL1() # balance on goerli network
```

### Transfer funds

Transfer funds among accounts on L2 network.

```python
receiver = account.create().address

transfer = wallet.transfer(
    TransferTransaction(to=Web3.to_checksum_address(receiver),
                        token_address=ADDRESS_DEFAULT,
                        amount=Web3.to_wei(0.1, "ether")))
```

### Deposit funds

Transfer funds from L1 to L2 network.

```python
transfer = wallet.deposit(
    DepositTransaction(token_address=ADDRESS_DEFAULT,
                        amount=Web3.to_wei(0.1, "ether")))
```

### Withdraw funds

Transfer funds from L2 to L1 network.

```python
transfer = wallet.deposit(
    WithdrawTransaction(token_address=ADDRESS_DEFAULT,
                        amount=Web3.to_wei(0.1, "ether")))
```

## 🤖Running Tests

In order to run test you need to run local-setup on your machine. For running tests, use:
```console
make wait
make prepare-tests
make run-tests
```

## 🤝 Contributing

We welcome contributions from the community! If you're interested in contributing to the `zksync2` Python SDK,
please take a look at our [CONTRIBUTING.md](./.github/CONTRIBUTING.md) for guidelines and details on the process.

Thank you for making `zksync2` Python SDK better! 🙌
