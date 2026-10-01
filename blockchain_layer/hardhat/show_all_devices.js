const hre = require("hardhat");

async function main() {
    const contractAddress = "0x882ad30E9e87867ACDdD0D219f5AcB56A5aC7F87";
    
    console.log("=".repeat(60));
    console.log("🔗 BLOCKCHAIN DEVICES");
    console.log("=".repeat(60));
    
    try {
        const contract = await hre.ethers.getContractAt("DeviceRegistry", contractAddress);
        const total = await contract.getTotalDevices();
        
        console.log(`\n📊 Total Devices on Blockchain: ${total.toString()}\n`);
        
        if(total == 0) {
            console.log("❌ No devices found on blockchain!");
            return;
        }
        
        console.log("=".repeat(60));
        console.log("📱 DEVICE LIST");
        console.log("=".repeat(60));
        
        for(let i = 0; i < total; i++) {
            try {
                const device = await contract.getDeviceByIndex(i);
                console.log(`\n${i+1}. 🆔 Virtual ID: ${device[0]}`);
                console.log(`   📱 Device Type: ${device[1]}`);
                console.log(`   🔑 Public Key: ${device[2].substring(0, 50)}...`);
                console.log(`   ⏰ Timestamp: ${new Date(device[3] * 1000).toLocaleString()}`);
                console.log(`   🔐 Status: ${device[4] ? '✅ Active' : '❌ Inactive'}`);
                console.log(`   👤 Owner: ${device[5]}`);
                console.log("-".repeat(50));
            } catch(e) {
                console.log(`\n${i+1}. ❌ Error reading device: ${e.message}`);
            }
        }
        
        console.log("\n" + "=".repeat(60));
        console.log(`✅ Total ${total} device(s) found on blockchain`);
        console.log("=".repeat(60));
        
    } catch(error) {
        console.error("❌ Error:", error.message);
        console.log("\n💡 Make sure:");
        console.log("   1. Ganache is running on port 7545");
        console.log("   2. Contract address is correct");
        console.log("   3. Network is configured properly");
    }
}

main().catch(console.error);
