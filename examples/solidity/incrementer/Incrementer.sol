// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

contract Incrementer {
    uint256 incrementer;
    uint256 value;

    constructor(uint _incrementer){
        incrementer = _incrementer;
        value = 0;
    }

    function increment() public {
        value += incrementer;
    }

    function get() public view returns (uint256) {
        return value;
    }
}
