// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DeviceRegistry {
    
    struct Device {
        string deviceId;
        string deviceType;
        string publicKey;
        uint256 registeredAt;
        bool isActive;
        address owner;
    }
    
    Device[] public devicesArray;
    mapping(string => uint256) public deviceIndexMap;
    mapping(string => bool) public deviceExists;
    
    event DeviceRegistered(string indexed deviceId, string deviceType, uint256 timestamp, address indexed owner);
    
    // Constructor - no validator needed
    constructor() {}
    
    // Register device - only public key, NO private key
    function registerDevice(
        string memory _deviceId,
        string memory _deviceType,
        string memory _publicKey
    ) public {
        require(!deviceExists[_deviceId], "Device already registered");
        require(bytes(_deviceId).length > 0, "Device ID cannot be empty");
        require(bytes(_publicKey).length > 0, "Public key cannot be empty");
        
        devicesArray.push(Device({
            deviceId: _deviceId,
            deviceType: _deviceType,
            publicKey: _publicKey,
            registeredAt: block.timestamp,
            isActive: true,
            owner: msg.sender
        }));
        
        deviceIndexMap[_deviceId] = devicesArray.length - 1;
        deviceExists[_deviceId] = true;
        
        emit DeviceRegistered(_deviceId, _deviceType, block.timestamp, msg.sender);
    }
    
    function getDevice(string memory _deviceId) 
        public 
        view 
        returns (
            string memory deviceId,
            string memory deviceType,
            string memory publicKey,
            uint256 registeredAt,
            bool isActive,
            address owner
        ) 
    {
        require(deviceExists[_deviceId], "Device does not exist");
        uint256 index = deviceIndexMap[_deviceId];
        Device storage device = devicesArray[index];
        return (
            device.deviceId,
            device.deviceType,
            device.publicKey,
            device.registeredAt,
            device.isActive,
            device.owner
        );
    }
    
    function getDeviceByIndex(uint256 index) public view returns (
        string memory deviceId,
        string memory deviceType,
        string memory publicKey,
        uint256 registeredAt,
        bool isActive,
        address owner
    ) {
        require(index < devicesArray.length, "Index out of bounds");
        Device storage device = devicesArray[index];
        return (
            device.deviceId,
            device.deviceType,
            device.publicKey,
            device.registeredAt,
            device.isActive,
            device.owner
        );
    }
    
    function getTotalDevices() public view returns (uint256) {
        return devicesArray.length;
    }
    
    function deactivateDevice(string memory _deviceId) public {
        require(deviceExists[_deviceId], "Device does not exist");
        uint256 index = deviceIndexMap[_deviceId];
        require(devicesArray[index].isActive, "Already inactive");
        require(devicesArray[index].owner == msg.sender, "Only owner can deactivate");
        devicesArray[index].isActive = false;
    }
}