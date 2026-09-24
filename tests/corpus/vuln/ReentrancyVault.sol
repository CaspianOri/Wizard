pragma solidity ^0.8.20;

contract ReentrancyVault {
    mapping(address => uint256) public balances;

    function withdraw() external {
        uint256 amount = balances[msg.sender];
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "failed");
        balances[msg.sender] = 0;
    }
}
