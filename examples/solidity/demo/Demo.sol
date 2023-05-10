// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

// demo Foo.sol from current directory
import "./Foo.sol";

// demo {symbol1 as alias, symbol2} from "filename";
import {Unauthorized, add as func, Point} from "./Foo.sol";

contract Demo {
    // Initialize Foo.sol
    Foo public foo = new Foo();

    // Test Foo.sol by getting it's name.
    function getFooName() public view returns (string memory) {
        return foo.name();
    }
}
