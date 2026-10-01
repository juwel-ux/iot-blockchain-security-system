const hre = require("hardhat");

async function main() {
    const contractAddress = "0x555abf9Dc4e31b14192C6A8e0aA817172e6dd948";
    const contract = await hre.ethers.getContractAt("DeviceRegistry", contractAddress);
    const total = await contract.getTotalDevices();
    
    console.log("\n" + "=".repeat(60));
    console.log("🔗 SYNCING DEVICES FROM SMART CONTRACT");
    console.log("=".repeat(60));
    console.log(`\n📊 Total Devices in Smart Contract: ${total}\n`);
    
    const devices = [];
    
    for(let i = 0; i < total; i++) {
        try {
            // Try different method names
            let device;
            try {
                device = await contract.getDeviceByIndex(i);
            } catch(e) {
                // If getDeviceByIndex doesn't exist, try alternative
                console.log(`   Method getDeviceByIndex not found, trying alternative...`);
                break;
            }
            
            console.log(`${i+1}. 🆔 ${device[0]}`);
            console.log(`   📱 Type: ${device[1]}`);
            console.log(`   ⏰ Time: ${new Date(device[3] * 1000).toLocaleString()}`);
            console.log(`   🔐 Status: ${device[4] ? "✅ Active" : "❌ Inactive"}`);
            console.log("-".repeat(40));
            devices.push(device[0]);
        } catch(e) {
            console.log(`   Error getting device ${i}: ${e.message}`);
        }
    }
    
    console.log("\n" + "=".repeat(60));
    console.log("📋 Device IDs found:");
    devices.forEach((vid, i) => console.log(`   ${i+1}. ${vid}`));
    console.log("=".repeat(60));
    
    // Output as JSON for API
    console.log("\n📊 JSON Output:");
    console.log(JSON.stringify({ devices, count: devices.length }, null, 2));
}

main().catch(console.error);
