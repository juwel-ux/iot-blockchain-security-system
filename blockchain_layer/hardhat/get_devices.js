const hre = require("hardhat");

async function main() {
    const contractAddress = "0x99637C402F5eE84784D8D878F842b064B78e5F22";
    const contract = await hre.ethers.getContractAt("DeviceRegistry", contractAddress);
    
    const total = await contract.getTotalDevices();
    console.log("Total devices on blockchain:", total.toString());
    console.log("=".repeat(50));
    
    for(let i = 0; i < total; i++) {
        try {
            const device = await contract.getDeviceByIndex(i);
            console.log(`${i+1}. ${device[0]}`);
        } catch(e) {
            console.log(`${i+1}. Error: ${e.message}`);
        }
    }
}

main().catch(console.error);
