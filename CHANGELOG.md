# [2.0.0](https://github.com/zksync-sdk/zksync2-python/compare/v1.2.0...v2.0.0) (2024-11-08)


### Bug Fixes

* `estimate_default_bridge_deposit_l2_gas` use correct token ([a173430](https://github.com/zksync-sdk/zksync2-python/commit/a173430e30f40e3cbc93cceca3581cec99b8e0c0))
* **wallet:** fix custom bridge support ([a095d5a](https://github.com/zksync-sdk/zksync2-python/commit/a095d5a21e92baaa58adde5a5e4f7f90a8f0bcfc))
* **wallet:** use `l2BridgeAddress` in `_get_l2_gas_limit_from_custom_bridge` ([b94636a](https://github.com/zksync-sdk/zksync2-python/commit/b94636a75ff3949256f8764bf658ba1f4cbfcbc8))


### Features

* `LegacyContractFactory` add `createAccount` and `create2Account` ([2daa365](https://github.com/zksync-sdk/zksync2-python/commit/2daa365ccc937721dcf647bd65afb28a307b4f8f))
* add `SmartAccount` feature ([15eb303](https://github.com/zksync-sdk/zksync2-python/commit/15eb303d5959d97348b4a81a007071a9dbd0c215))
* improve `provider` typing ([215168c](https://github.com/zksync-sdk/zksync2-python/commit/215168c4654a2f3f8ccea3952f3dbbd0808434c5))
* **provider:** add `is_l2_bridge_legacy` ([5cb4eb8](https://github.com/zksync-sdk/zksync2-python/commit/5cb4eb8b8f312a2e19a61d994254abe5604360db))
* **provider:** add `zks_get_confirmed_tokens` ([fc72cf9](https://github.com/zksync-sdk/zksync2-python/commit/fc72cf9ed637b0843e1f7bc784d94a7b31310cb6))
* **provider:** add `zks_get_fee_params` ([82848dc](https://github.com/zksync-sdk/zksync2-python/commit/82848dccd1807e7dcff3f095dc711b77f4514b03))
* **provider:** add `zks_get_protocol_version` ([5005ef1](https://github.com/zksync-sdk/zksync2-python/commit/5005ef13db214c909dccecc796477b0ccaaa76eb))
* **provider:** add `zks_send_raw_transaction_with_detailed_output` ([b306242](https://github.com/zksync-sdk/zksync2-python/commit/b3062420992c80d5534a380981e1097be447961d))
* update `web3` to the latest version ([cd0c34c](https://github.com/zksync-sdk/zksync2-python/commit/cd0c34cb3c3afd48a75bab692ad23dc8a3e52d1c))
* **wallet:** add `l1_token_address` ([b6c49d3](https://github.com/zksync-sdk/zksync2-python/commit/b6c49d3d9acc0bb5dcb60ab9092278498dc6c699))


### BREAKING CHANGES

* update to `web3` `v7`

# [1.2.0](https://github.com/zksync-sdk/zksync2-python/compare/v1.1.0...v1.2.0) (2024-06-07)


### Bug Fixes

* fix abi contract cache ([81b9e4c](https://github.com/zksync-sdk/zksync2-python/commit/81b9e4c8bec9cd2fc258669edeb8012ccafa0c80))
* non zero gas limit in options breaks transfer function ([d739a60](https://github.com/zksync-sdk/zksync2-python/commit/d739a604f7ff43bc372586377d861d66745980b4))
* zks_l1_chain_id not returning int type ([0ebd1b8](https://github.com/zksync-sdk/zksync2-python/commit/0ebd1b8499d22b1c83a1051b77a461841e1a4f0d))


### Features

* provide support for Bridgehub ([dabbfc0](https://github.com/zksync-sdk/zksync2-python/commit/dabbfc0c95f11e79e6683101b20fae3c851506e8))

# [1.2.0](https://github.com/zksync-sdk/zksync2-python/compare/v1.1.0...v1.2.0) (2024-06-07)


### Bug Fixes

* fix abi contract cache ([81b9e4c](https://github.com/zksync-sdk/zksync2-python/commit/81b9e4c8bec9cd2fc258669edeb8012ccafa0c80))
* non zero gas limit in options breaks transfer function ([d739a60](https://github.com/zksync-sdk/zksync2-python/commit/d739a604f7ff43bc372586377d861d66745980b4))
* zks_l1_chain_id not returning int type ([0ebd1b8](https://github.com/zksync-sdk/zksync2-python/commit/0ebd1b8499d22b1c83a1051b77a461841e1a4f0d))


### Features

* provide support for Bridgehub ([dabbfc0](https://github.com/zksync-sdk/zksync2-python/commit/dabbfc0c95f11e79e6683101b20fae3c851506e8))

# [1.1.0](https://github.com/zksync-sdk/zksync2-python/compare/v1.0.0...v1.1.0) (2024-02-18)


### Features

* paymster withdraw and transfer support ([66f7761](https://github.com/zksync-sdk/zksync2-python/commit/66f7761bf4a1677ed50a6bf995e0fde6515b76b7))
* **provider:** add zks_logProof ([6d48dff](https://github.com/zksync-sdk/zksync2-python/commit/6d48dff8e7e81709b637d2117ba6a2c843e9d740))

# [1.0.0](https://github.com/zksync-sdk/zksync2-python/compare/v0.6.0...v1.0.0) (2024-01-19)


### Bug Fixes

* `withdraw` bridge address ([6334874](https://github.com/zksync-sdk/zksync2-python/commit/6334874c8022407ce360b0bd35118fb7cbad66d1))
* `withdraw` token bridge address ([6d5b45c](https://github.com/zksync-sdk/zksync2-python/commit/6d5b45c334dde44ad9bdc83642f458950fd722a6))
* `withdraw` token bridge address ([279bfd8](https://github.com/zksync-sdk/zksync2-python/commit/279bfd874f7b998b4dd2e00165433e9990d29c74))
* relax web3 version restriction ([5d50182](https://github.com/zksync-sdk/zksync2-python/commit/5d5018242c3d4cae1957c99a43944eb4652b9cc1))
* resolve issue relate to `wETH` bridge ([48ac8cd](https://github.com/zksync-sdk/zksync2-python/commit/48ac8cd5aac80214a9be399bcade222f8d97dd2c))


### Features

* add `WalletL1`, `WalletL2` and `Wallet` ([b189068](https://github.com/zksync-sdk/zksync2-python/commit/b1890685638192edc7279a2273ae14ee41e2c904))
* remove deprications ([d2f2ce7](https://github.com/zksync-sdk/zksync2-python/commit/d2f2ce707847404787539a88ee0f573fe6d806f2))


### BREAKING CHANGES

* remove all deprications

## [0.6.0](https://github.com/zksync-sdk/zksync2-python/compare/v0.5.0...v0.6.0) (2023-07-07)

### Features

*  add account abstraction and paymaster features ([28f930c](https://github.com/zksync-sdk/zksync2-python/commit/28f930ce6e68f11110c0afc7c8c0f5fc2253ab28))
