const hre = require("hardhat");

async function main() {
  console.log("Deploying DeviceRegistry contract...");
  
  const DeviceRegistry = await hre.ethers.getContractFactory("DeviceRegistry");
  const deviceRegistry = await DeviceRegistry.deploy();
  
  await deviceRegistry.waitForDeployment();
  
  const address = await deviceRegistry.getAddress();
  console.log("✅ DeviceRegistry deployed to:", address);
  
  // Save address to file
  const fs = require('fs');
  fs.writeFileSync('contract_address.txt', address);
  console.log("📁 Contract address saved to contract_address.txt");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
