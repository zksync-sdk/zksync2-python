# How to Compile Solidity Smart Contracts

Use `zksolc` compiler to compile Solidity smart contracts. 
`zksolc` compiler requires `solc` to be installed. Specific version of
`zksolc` compiler is compatible with specific versions `solc` so make
sure to make correct versions of your compilers.

There are 3 solidity smart contracts:

- `Storage`: contract without constructor.
- `Incrementer`: contract with constructor.
- `Demo`: contract that has dependency to `Foo` contract.

In following examples `Docker` is used to create containers with already
`solc` installed. 

## Compile Smart Contracts

Run the container has `solc` tool already installed:
```shell
# create container with installed solc tool
SOLC_VERSION="0.8.19-alpine"
docker create -it --name zksolc --entrypoint ash  ethereum/solc:${SOLC_VERSION}

# copy smart contracts source files to container
docker cp examples/solidity zksolc:/solidity

# run and attach to the container
docker start -i zksolc
```
Run commands in container:
```shell
# download zksolc
ZKSOLC_VERSION="v1.3.9"
wget https://github.com/matter-labs/zksolc-bin/raw/main/linux-amd64/zksolc-linux-amd64-musl-${ZKSOLC_VERSION} -O /bin/zksolc; chmod +x /bin/zksolc
```

**Compile Storage Smart Contract**
```shell
# create combined-json with abi and binary
zksolc -O3 -o solidity/storage/build \
  --combined-json abi,bin \
  solidity/storage/Storage.sol
```

**Compile Incrementer Smart Contract**
```shell
# create combined-json with abi and binary
zksolc -O3 -o solidity/incrementer/build \
  --combined-json abi,bin \
  solidity/incrementer/Incrementer.sol
```

**Compile Demo Smart Contract**
```shell
# create combined-json with abi and binary
zksolc -O3 -o solidity/demo/build \
  --combined-json abi,bin \
  solidity/demo/Demo.sol \
  solidity/demo/Foo.sol
```
Exit from container
```shell
exit 
```

Copy generated files from container to host machine
```shell
# copy generated files from container to host
docker cp zksolc:/solidity ./examples/

# remove container
docker rm zksolc
```

On host machine, for each smart contract there is `build/combined.json` file
(e.g. `solidity/storage/build/combined.json`) that can be used in program for 
deploying and interacting with smart contract.