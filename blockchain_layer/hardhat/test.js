const hre = require("hardhat");

async function main() {
    const contractAddress = "0x555abf9Dc4e31b14192C6A8e0aA817172e6dd948";
    const contract = await hre.ethers.getContractAt("DeviceRegistry", contractAddress);
    
    console.log("\ngetDeviceByIndex:", typeof contract.getDeviceByIndex === 'function' ? "✅ YES" : "❌ NO");
    
    const total = await contract.getTotalDevices();
    console.log("Total Devices:", total.toString());
    
    if (typeof contract.getDeviceByIndex === 'function' && total > 0) {
        for(let i = 0; i < total; i++) {
            const d = await contract.getDeviceByIndex(i);
            console.log(`\n${i+1}. ${d[0]}`);
            console.log(`   Type: ${d[1]}`);
        }
    }
}

main().catch(console.error);
