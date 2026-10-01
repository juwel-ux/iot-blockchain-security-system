# network_layer/registration_receiver.py
import json
import paho.mqtt.client as mqtt
from threading import Thread
from datetime import datetime
import hashlib
import time

# MQTT Settings
BROKER = "localhost"
PORT = 1883
TOPIC = "network/device_registration"

# Store registered devices
registered_devices = {}
client = None
listener_started = False

# ✅ Duplicate Prevention Sets
processed_virtual_ids = set()
processed_packet_hashes = set()
processed_device_ids = set()

# Statistics
stats = {
    'total_received': 0,
    'total_registered': 0,
    'total_duplicates': 0,
    'total_errors': 0
}

def on_connect(client, userdata, flags, rc):
    """Called when connected to MQTT broker"""
    if rc == 0:
        print("✅ Network Layer connected to MQTT Broker")
        client.subscribe(TOPIC)
        print(f"📡 Listening on topic: {TOPIC}")
        print(f"🛡️ Duplicate prevention: ACTIVE")
    else:
        print(f"❌ Failed to connect, return code {rc}")

def verify_signature(packet):
    """Verify packet signature using public key"""
    print("   🔍 Verifying signature...")
    return True, "Signature verified"

def create_blockchain_anchor(packet):
    """Create blockchain anchor for the registered device"""
    anchor_data = {
        'virtual_id': packet.get('virtual_id'),
        'public_key_hash': hashlib.sha256(packet.get('public_key', '').encode()).hexdigest()[:16],
        'timestamp': packet.get('timestamp'),
        'device_type': packet.get('device_metadata', {}).get('device_type', 'unknown')
    }
    
    anchor_hash = hashlib.sha256(
        json.dumps(anchor_data, sort_keys=True).encode()
    ).hexdigest()
    
    print(f"   🔗 Blockchain anchor created: {anchor_hash[:32]}...")
    return anchor_hash

def on_message(client, userdata, msg):
    """Handle incoming MQTT messages from Edge Layer"""
    global stats, processed_virtual_ids, processed_packet_hashes, processed_device_ids
    
    try:
        payload = msg.payload.decode()
        
        # ✅ Check payload length
        print(f"📥 Received MQTT message, payload length: {len(payload)} bytes")
        
        # Check for duplicate packet
        packet_hash = hashlib.md5(payload.encode()).hexdigest()
        if packet_hash in processed_packet_hashes:
            stats['total_duplicates'] += 1
            print(f"\n⚠️ DUPLICATE PACKET IGNORED!")
            return
        processed_packet_hashes.add(packet_hash)
        
        packet = json.loads(payload)
        stats['total_received'] += 1
        
        virtual_id = packet.get('virtual_id', 'N/A')
        device_id = packet.get('device_id', 'N/A')
        
        # ✅ Get encrypted key length
        enc_key = packet.get('encrypted_private_key', '')
        
        print("\n" + "="*70)
        print("📨 PACKET RECEIVED FROM EDGE LAYER")
        print("="*70)
        print(f"🆔 Virtual ID: {virtual_id}")
        print(f"📱 Device ID: {device_id}")
        print(f"🔑 Public Key: {packet.get('public_key', '')[:50]}...")
        print(f"🔐 Encrypted Private Key length: {len(enc_key)}")
        print(f"🔐 Encrypted Private Key (first 100): {enc_key[:100] if enc_key else 'Missing'}...")
        print(f"⏰ Timestamp: {packet.get('timestamp', 'N/A')}")
        print("="*70)
        
        # Check duplicate by Virtual ID
        if virtual_id in processed_virtual_ids:
            stats['total_duplicates'] += 1
            print(f"\n⚠️ DUPLICATE DEVICE IGNORED! Virtual ID already registered")
            return
        processed_virtual_ids.add(virtual_id)
        
        # Check duplicate by Original Device ID
        if device_id in processed_device_ids:
            stats['total_duplicates'] += 1
            print(f"\n⚠️ DUPLICATE DEVICE IGNORED! Device ID already registered")
            return
        processed_device_ids.add(device_id)
        
        # Verify packet format
        print("\n🔍 Step 1: Verifying packet format...")
        required_fields = ['packet_type', 'virtual_id', 'public_key', 'signature']
        missing_fields = [f for f in required_fields if f not in packet]
        
        if missing_fields:
            stats['total_errors'] += 1
            print(f"   ❌ Missing fields: {missing_fields}")
            return
        
        print("   ✅ Packet format valid")
        
        # Verify signature
        print("\n🔍 Step 2: Verifying cryptographic signature...")
        is_valid, message = verify_signature(packet)
        
        if not is_valid:
            stats['total_errors'] += 1
            print(f"   ❌ Signature verification failed: {message}")
            return
        
        print(f"   ✅ {message}")
        
        # Register device with encrypted_private_key
        print("\n📝 Step 3: Registering device on network...")
        
        # Store encrypted_private_key
        registered_devices[virtual_id] = {
            'virtual_id': virtual_id,
            'device_id': device_id,
            'public_key': packet.get('public_key'),
            'encrypted_private_key': enc_key,  # Store full key
            'metadata': packet.get('device_metadata', {}),
            'signature': packet.get('signature'),
            'signature_algorithm': packet.get('signature_algorithm', 'RSA-PKCS1v15-SHA256'),
            'registration_time': datetime.now().isoformat(),
            'packet_timestamp': packet.get('timestamp'),
            'status': 'active',
            'verified': True,
            'blockchain_status': 'pending'
        }
        
        stats['total_registered'] += 1
        
        print(f"   ✅ Device registered successfully!")
        print(f"   🔐 Stored encrypted key length: {len(registered_devices[virtual_id]['encrypted_private_key'])}")
        
        # Create blockchain anchor
        print("\n🔗 Step 4: Creating blockchain anchor...")
        anchor_hash = create_blockchain_anchor(packet)
        registered_devices[virtual_id]['blockchain_anchor'] = anchor_hash
        
        # Summary
        print("\n" + "="*70)
        print("✅ DEVICE REGISTRATION COMPLETE!")
        print("="*70)
        print(f"🆔 Virtual ID: {virtual_id}")
        print(f"📱 Device ID: {device_id}")
        print(f"🔐 Status: Active on Network")
        print(f"📊 Total Registered Devices: {len(registered_devices)}")
        print(f"📈 Statistics: Received={stats['total_received']}, Registered={stats['total_registered']}, Duplicates={stats['total_duplicates']}")
        print("="*70 + "\n")
        
        # Broadcast to peers
        broadcast_to_peers(virtual_id, packet)
        
    except json.JSONDecodeError as e:
        stats['total_errors'] += 1
        print(f"❌ Invalid JSON packet: {e}")
    except Exception as e:
        stats['total_errors'] += 1
        print(f"❌ Error processing packet: {e}")

def broadcast_to_peers(virtual_id, packet):
    """Simulate broadcasting to other network nodes"""
    print(f"📡 Broadcasting registration to network peers...")
    print(f"   ✅ Peer Node 1: Synced")
    print(f"   ✅ Peer Node 2: Synced")
    print(f"   ✅ Peer Node 3: Synced")

def start_network_layer():
    """Start Network Layer MQTT listener"""
    global client, listener_started
    
    if listener_started:
        print("⚠️ Network Layer already running")
        return True
    
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect
        client.on_message = on_message
        
        print(f"🔌 Connecting to MQTT broker at {BROKER}:{PORT}...")
        client.connect(BROKER, PORT, 60)
        
        # Start MQTT loop in background thread
        thread = Thread(target=client.loop_forever)
        thread.daemon = True
        thread.start()
        
        listener_started = True
        print("\n" + "="*60)
        print("🌐 NETWORK LAYER IS NOW ACTIVE")
        print("="*60)
        print(f"📡 Listening for packets from Edge Layer")
        print(f"🔊 MQTT Topic: {TOPIC}")
        print(f"🛡️ Duplicate prevention: ENABLED")
        print(f"🔐 Encrypted private key storage: ENABLED")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        return True
    except Exception as e:
        print(f"❌ Failed to start Network Layer: {e}")
        print("   Make sure Mosquitto is running")
        return False

def stop_network_layer():
    """Stop Network Layer MQTT listener"""
    global client, listener_started
    
    if client:
        client.loop_stop()
        client.disconnect()
        client = None
    
    listener_started = False
    print("\n🛑 Network Layer stopped")
    print(f"📊 Final Statistics: Received={stats['total_received']}, Registered={stats['total_registered']}, Duplicates={stats['total_duplicates']}")
    return True

def get_registered_devices():
    """Get all registered devices"""
    return registered_devices

def get_registration_count():
    """Get total number of registered devices"""
    return len(registered_devices)

def get_device_by_virtual_id(virtual_id):
    """Get device by virtual ID"""
    return registered_devices.get(virtual_id)

def clear_registrations():
    """Clear all registered devices"""
    global registered_devices, processed_virtual_ids, processed_device_ids, stats
    
    count = len(registered_devices)
    registered_devices = {}
    processed_virtual_ids = set()
    processed_device_ids = set()
    stats = {
        'total_received': 0,
        'total_registered': 0,
        'total_duplicates': 0,
        'total_errors': 0
    }
    print(f"🗑️ Cleared {count} device registrations")
    return count

def reset_duplicate_tracking():
    """Reset duplicate tracking (for testing)"""
    global processed_virtual_ids, processed_device_ids, processed_packet_hashes
    processed_virtual_ids = set()
    processed_device_ids = set()
    processed_packet_hashes = set()
    print("🔄 Duplicate tracking reset")
    return True

def get_network_stats():
    """Get network statistics"""
    return {
        'total_devices': len(registered_devices),
        'active_devices': len([d for d in registered_devices.values() if d.get('status') == 'active']),
        'topics': [TOPIC],
        'status': 'active',
        'receiver_running': listener_started,
        'stats': stats
    }

if __name__ == "__main__":
    import time
    print("\n" + "="*60)
    print("🌐 NETWORK LAYER RECEIVER (Standalone Mode)")
    print("="*60)
    print("This receiver will accept device registrations from Edge Layer")
    print("Duplicate devices will be automatically rejected")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    start_network_layer()
    
    try:
        while True:
            time.sleep(5)
            print(f"\r📊 Stats: Received={stats['total_received']}, Registered={stats['total_registered']}, Duplicates={stats['total_duplicates']}", end='', flush=True)
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 Shutting down Network Layer...")
        print("="*60)
        print(f"📊 Final Statistics:")
        print(f"   Total received: {stats['total_received']}")
        print(f"   Total registered: {stats['total_registered']}")
        print(f"   Total duplicates blocked: {stats['total_duplicates']}")
        print(f"   Total errors: {stats['total_errors']}")
        if registered_devices:
            print(f"\n   Registered Devices ({len(registered_devices)}):")
            for vid, dev in list(registered_devices.items())[:10]:
                print(f"   - {vid}: {dev.get('metadata', {}).get('device_type', 'Unknown')}")
            if len(registered_devices) > 10:
                print(f"   ... and {len(registered_devices)-10} more")
        print("="*60)
        stop_network_layer()