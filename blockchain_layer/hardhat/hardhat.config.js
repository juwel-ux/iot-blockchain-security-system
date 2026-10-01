require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.19",
  networks: {
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      gas: 3000000,
      gasPrice: 20000000000,
      accounts: {
        mnemonic: "owner mass wrong dawn decline dance text switch expose royal color leg",
        count: 10,
      },
    },
  },
};
