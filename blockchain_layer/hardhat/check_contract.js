const hre = require("hardhat");

async function main() {
    const contractAddress = "0x555abf9Dc4e31b14192C6A8e0aA817172e6dd948";
    const contract = await hre.ethers.getContractAt("DeviceRegistry", contractAddress);
    const total = await contract.getTotalDevices();
    
    console.log("\n" + "=".repeat(60));
    console.log("🔗 SMART CONTRACT DEVICES");
    console.log("=".repeat(60));
    console.log(`\n📊 Total Devices: ${total}\n`);
    
    if(total == 0) {
        console.log("❌ No devices found in smart contract!");
    } else {
        for(let i = 0; i < total; i++) {
            const device = await contract.getDeviceByIndex(i);
            console.log(`${i+1}. 🆔 ${device[0]}`);
            console.log(`   📱 Type: ${device[1]}`);
            console.log(`   ⏰ Time: ${new Date(device[3] * 1000).toLocaleString()}`);
            console.log(`   🔐 Status: ${device[4] ? "✅ Active" : "❌ Inactive"}`);
            console.log(`   👤 Owner: ${device[5]}`);
            console.log("-".repeat(50));
        }
    }
    console.log("\n" + "=".repeat(60));
}

main().catch(console.error);
