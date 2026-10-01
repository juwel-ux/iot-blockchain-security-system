import time
import json

def create_registration_packet(device_id, device_type):
    """
    Create a registration packet for a device
    """
    packet = {
        "device_id": device_id,
        "device_type": device_type,
        "timestamp": int(time.time())  # Unix timestamp
    }
    return packet

# ----------------------------
# Example usage
# ----------------------------
if __name__ == "__main__":
    device_id = "VDEV_1234-5678-9012"
    device_type = "virtual"
    
    packet = create_registration_packet(device_id, device_type)
    
    # Print as JSON string (for network transmission)
    packet_json = json.dumps(packet)
    print("Device Registration Packet:")
    print(packet_json)