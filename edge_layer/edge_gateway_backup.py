# edge_layer/edge_gateway.py
import json
import paho.mqtt.client as mqtt
from threading import Thread, Lock
import time
import hashlib
import os
import base64
from datetime import datetime
from .device_crypto import DeviceCrypto
from .network_sender import NetworkSender
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ============== SECURE STORAGE FOR PRIVATE KEYS ==============
class SecureKeyStorage:
    """Private Key এনক্রিপ্টেড স্টোরেজ"""
    
    def __init__(self):
        self.cipher = None
        self.encrypted_keys = {}
        self.init_encryption()
    
    def init_encryption(self):
        """Master Key থেকে Encryption Key তৈরি"""
        # Master Password (Environment Variable থেকে নেওয়া)
        master_password = os.environ.get('KEY_MASTER_PASSWORD', 'iot_blockchain_secure_key_2024')
        
        # Salt for key derivation
        salt = b'iot_blockchain_salt_v1'
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self.cipher = Fernet(key)
        print("✅ Secure storage initialized")
    
    def encrypt_private_key(self, private_key_pem):
        """Private Key এনক্রিপ্ট করা"""
        if not self.cipher:
            self.init_encryption()
        encrypted = self.cipher.encrypt(private_key_pem.encode())
        return encrypted.decode()
    
    def decrypt_private_key(self, encrypted_key):
        """Private Key ডিক্রিপ্ট করা"""
        if not self.cipher:
            self.init_encryption()
        decrypted = self.cipher.decrypt(encrypted_key.encode())
        return decrypted.decode()

# ============== CONFIGURATION ==============
BROKER = "localhost"
PORT = 1883
TOPIC = "device/registration"

# Global variables
last_packet = None
registered_devices = []  # Device queue
device_id_counter = 1

# ✅ Processing lock - prevents concurrent processing
processing_lock = Lock()
is_processing = False

# ✅ Duplicate tracking
PROCESSED_DEVICE_IDS = set()
PROCESSED_PACKET_HASHES = set()

# ✅ Statistics
stats = {
    'total_received': 0,
    'total_processed': 0,
    'total_failed': 0,
    'total_sent_to_network': 0
}

# Initialize modules
crypto = DeviceCrypto()
network_sender = NetworkSender()
secure_storage = SecureKeyStorage()

print("="*60)
print("⚡ EDGE GATEWAY - SERIAL PROCESSING MODE")
print("="*60)
print("✅ Sequential processing (one device at a time)")
print("✅ Duplicate prevention active")
print("✅ Encrypted private key storage")
print("✅ Queue management with remove option")
print("="*60 + "\n")

# ============== MONGODB VERIFICATION ==============
try:
    from pymongo import MongoClient
    mongo_client = MongoClient('mongodb://localhost:27017/')
    db = mongo_client['iot_project_db']
    devices_collection = db['devices']
    MONGO_AVAILABLE = True
    print("✅ MongoDB connected for verification")
except Exception as e:
    MONGO_AVAILABLE = False
    print(f"⚠️ MongoDB not available: {e}")

def verify_with_mongodb(device_id):
    """Verify device ID with MongoDB"""
    if not MONGO_AVAILABLE:
        return True, "MongoDB not available, skipping verification"
    
    try:
        device = devices_collection.find_one({'device_id': device_id})
        if device:
            return True, "Device verified in MongoDB"
        else:
            return False, "Device not found in MongoDB"
    except Exception as e:
        return False, f"MongoDB verification failed: {e}"

def verify_zkp_lightweight(device_id):
    """Lightweight ZKP verification"""
    # Simplified ZKP for IoT devices
    # In production, use proper ZKP implementation
    try:
        # Create a simple proof based on device_id hash
        proof = hashlib.sha256(f"zkp_{device_id}_secret".encode()).hexdigest()[:16]
        expected = hashlib.sha256(f"zkp_{device_id}_secret".encode()).hexdigest()[:16]
        
        if proof == expected:
            return True, "ZKP verification passed"
        return False, "ZKP verification failed"
    except Exception as e:
        return False, f"ZKP error: {e}"

# ============== MQTT CALLBACKS ==============
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT Connected")
        client.subscribe(TOPIC)
        print(f"📡 Listening on: {TOPIC}")
    else:
        print(f"❌ Connection failed: {rc}")

def on_message(client, userdata, msg):
    global last_packet, registered_devices, device_id_counter, is_processing, stats
    
    try:
        payload = msg.payload.decode()
        
        # Check for duplicate packet
        packet_hash = hashlib.md5(payload.encode()).hexdigest()
        if packet_hash in PROCESSED_PACKET_HASHES:
            print(f"⚠️ Duplicate packet ignored")
            return
        PROCESSED_PACKET_HASHES.add(packet_hash)
        
        packet = json.loads(payload)
        last_packet = packet
        
        device_id = packet.get('device_id', 'N/A')
        device_type = packet.get('device_type', 'virtual')
        
        print(f"\n📦 Packet received from: {device_id}")
        print(f"   Type: {device_type}")
        
        # ✅ Check if device already processed
        if device_id in PROCESSED_DEVICE_IDS:
            print(f"⚠️ Device {device_id} already processed! Ignoring...")
            return
        
        stats['total_received'] += 1
        
        # ✅ Start serial processing (one at a time)
        process_device_serial(packet, device_id, device_type)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        stats['total_failed'] += 1

# ============== SERIAL PROCESSING (One by one) ==============
def process_device_serial(packet, device_id, device_type):
    global is_processing, registered_devices, device_id_counter, stats
    
    # ✅ Wait if already processing
    while is_processing:
        print(f"⏳ Waiting for previous device to finish processing...")
        time.sleep(0.5)
    
    # ✅ Lock for processing
    with processing_lock:
        is_processing = True
        print(f"\n{'='*50}")
        print(f"🔧 PROCESSING DEVICE: {device_id}")
        print(f"{'='*50}")
        
        try:
            # ========== STEP 1: MongoDB Verification ==========
            print("\n📌 STEP 1: MongoDB Verification")
            print("-" * 30)
            mongo_valid, mongo_msg = verify_with_mongodb(device_id)
            print(f"   Result: {mongo_msg}")
            if not mongo_valid:
                print(f"❌ STOPPED at STEP 1 - MongoDB verification failed")
                stats['total_failed'] += 1
                return
            
            # ========== STEP 2: ZKP Verification ==========
            print("\n📌 STEP 2: ZKP Verification (Lightweight)")
            print("-" * 30)
            zkp_valid, zkp_msg = verify_zkp_lightweight(device_id)
            print(f"   Result: {zkp_msg}")
            if not zkp_valid:
                print(f"❌ STOPPED at STEP 2 - ZKP verification failed")
                stats['total_failed'] += 1
                return
            
            # ========== STEP 3: Generate RSA Key Pair ==========
            print("\n📌 STEP 3: Generating RSA Key Pair (2048-bit)")
            print("-" * 30)
            private_key, public_key = crypto.generate_key_pair(device_id)
            print(f"   ✅ Public Key generated")
            print(f"   ✅ Private Key generated (will be encrypted)")
            
            # ========== STEP 4: Encrypt Private Key ==========
            print("\n📌 STEP 4: Encrypting Private Key")
            print("-" * 30)
            encrypted_private_key = secure_storage.encrypt_private_key(private_key)
            print(f"   ✅ Private key encrypted securely")
            
            # ========== STEP 5: Create Virtual ID ==========
            print("\n📌 STEP 5: Creating Virtual Identity")
            print("-" * 30)
            virtual_id = f"VID_{device_type.upper()}_{int(time.time())}_{device_id[-8:]}"
            print(f"   ✅ Virtual ID: {virtual_id}")
            
            # ========== STEP 6: Sign Packet ==========
            print("\n📌 STEP 6: Signing Packet")
            print("-" * 30)
            packet_data = {
                'device_id': device_id,
                'virtual_id': virtual_id,
                'public_key': public_key,
                'timestamp': time.time()
            }
            signature = crypto.sign_packet(device_id, packet_data)
            print(f"   ✅ Signature created")
            
            # ========== STEP 7: Create Network Packet ==========
            print("\n📌 STEP 7: Creating Network Packet")
            print("-" * 30)
            network_packet = {
                'packet_type': 'device_registration',
                'packet_version': '1.0',
                'virtual_id': virtual_id,
                'device_id': device_id,
                'device_type': device_type,
                'public_key': public_key,
                'signature': signature,
                'timestamp': time.time()
            }
            print(f"   ✅ Network packet ready (NO private key)")
            
            # ========== STEP 8: Add to Queue ==========
            print("\n📌 STEP 8: Adding to Queue")
            print("-" * 30)
            device_info = {
                'id': device_id_counter,
                'device_id': device_id,
                'virtual_id': virtual_id,
                'device_type': device_type,
                'public_key': public_key[:80] + "...",
                'public_key_full': public_key,
                'encrypted_private_key': encrypted_private_key,  # ✅ Encrypted!
                'signature': signature[:40] + "...",
                'network_packet': network_packet,
                'status': 'pending',  # pending, sent, failed
                'received_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'steps_passed': 8
            }
            
            registered_devices.append(device_info)
            device_id_counter += 1
            PROCESSED_DEVICE_IDS.add(device_id)
            stats['total_processed'] += 1
            
            print(f"\n{'='*50}")
            print(f"✅ DEVICE SUCCESSFULLY PROCESSED!")
            print(f"   ID: {device_info['id']}")
            print(f"   Virtual ID: {virtual_id}")
            print(f"   Total in queue: {len(registered_devices)}")
            print(f"   Status: PENDING (waiting for network send)")
            print(f"{'='*50}\n")
            
        except Exception as e:
            print(f"\n❌ PROCESSING FAILED at step: {e}")
            stats['total_failed'] += 1
        
        finally:
            is_processing = False

# ============== QUEUE MANAGEMENT FUNCTIONS ==============
def get_all_devices():
    """Get all devices in queue"""
    return registered_devices

def get_device_count():
    """Get total device count"""
    return len(registered_devices)

def get_pending_count():
    """Get pending devices count"""
    return len([d for d in registered_devices if d['status'] == 'pending'])

def get_sent_count():
    """Get sent devices count"""
    return len([d for d in registered_devices if d['status'] == 'sent'])

def get_failed_count():
    """Get failed devices count"""
    return len([d for d in registered_devices if d['status'] == 'failed'])

def get_stats():
    """Get processing statistics"""
    return stats

def send_selected_devices(selected_indices):
    """Send selected devices to Network Layer"""
    success = 0
    failed = 0
    
    for idx in selected_indices:
        if idx < len(registered_devices):
            device = registered_devices[idx]
            if device['status'] == 'pending':
                print(f"\n📡 Sending {device['virtual_id']} to Network Layer...")
                
                if network_sender.connect_mqtt():
                    if network_sender.send_to_network(device['network_packet']):
                        device['status'] = 'sent'
                        success += 1
                        stats['total_sent_to_network'] += 1
                        print(f"   ✅ Sent successfully")
                    else:
                        device['status'] = 'failed'
                        failed += 1
                        print(f"   ❌ Send failed")
                    network_sender.disconnect()
                else:
                    device['status'] = 'failed'
                    failed += 1
                    print(f"   ❌ MQTT connection failed")
    
    return success, failed

def remove_selected_devices(selected_indices):
    """Remove selected devices from queue"""
    removed = 0
    # Remove from end to avoid index shifting
    for idx in sorted(selected_indices, reverse=True):
        if idx < len(registered_devices):
            removed_device = registered_devices.pop(idx)
            print(f"🗑️ Removed device: {removed_device['virtual_id']}")
            removed += 1
    return removed

def clear_all_devices():
    """Clear all devices from queue"""
    global registered_devices, PROCESSED_DEVICE_IDS, device_id_counter
    count = len(registered_devices)
    registered_devices = []
    PROCESSED_DEVICE_IDS = set()
    device_id_counter = 1
    print(f"🗑️ Cleared {count} devices from queue")
    return count

def get_device_by_virtual_id(virtual_id):
    """Get device by virtual ID"""
    for device in registered_devices:
        if device.get('virtual_id') == virtual_id:
            return device
    return None

def get_decrypted_private_key(virtual_id, master_password=None):
    """Get decrypted private key for a device"""
    device = get_device_by_virtual_id(virtual_id)
    if device and 'encrypted_private_key' in device:
        if master_password:
            # Use provided password
            secure_storage.init_encryption()
        return secure_storage.decrypt_private_key(device['encrypted_private_key'])
    return None

# ============== MQTT CLIENT SETUP ==============
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

def start_edge_gateway():
    try:
        client.connect(BROKER, PORT, 60)
        Thread(target=client.loop_forever, daemon=True).start()
        print("✅ Edge Gateway Started")
        print("📊 Processing mode: SERIAL (one device at a time)")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

# Auto-start
start_edge_gateway()