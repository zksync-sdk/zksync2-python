// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

contract Storage {
    uint256 counter;

    function set(uint256 _value) public {
        counter = _value;
    }

    function get() public view returns (uint256) {
        return counter;
    }
}
