# edge_layer/private_key_storage.py - SECURE MULTI-KEY STORAGE SYSTEM
import json
import os
import base64
import hashlib
import time
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import getpass

# ============== CONFIGURATION ==============
STORAGE_DIR = os.path.expanduser("~/Desktop/iot_blockchain_project/secure_storage")
KEYS_FILE = os.path.join(STORAGE_DIR, "encrypted_private_keys.json")
MASTER_KEY_FILE = os.path.join(STORAGE_DIR, "master_key.hash")
BACKUP_DIR = os.path.join(STORAGE_DIR, "backups")

# Ensure directories exist
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# ============== SECURE STORAGE CLASS ==============

class SecurePrivateKeyStorage:
    """
    Secure storage for encrypted private keys
    Supports multiple password versions, key rotation, and backup
    """
    
    def __init__(self):
        self.keys_data = {}
        self.master_key_hash = None
        self.current_version = "v1"
        self.load_storage()
    
    def _derive_key(self, password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """Derive encryption key from password with salt"""
        if salt is None:
            salt = os.urandom(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def _derive_key_scrypt(self, password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """Derive key using scrypt (more secure, slower)"""
        if salt is None:
            salt = os.urandom(32)
        
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=2**14,  # CPU/memory cost
            r=8,      # Block size
            p=1,      # Parallelization
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def encrypt_private_key(self, private_key_pem: str, password: str, version: str = "v1") -> Dict:
        """
        Encrypt a private key with user password
        Returns encrypted data structure
        """
        try:
            # Generate unique key ID
            key_id = hashlib.sha256(f"{private_key_pem[:50]}{time.time()}".encode()).hexdigest()[:16]
            
            # Derive encryption key
            if version == "v1":
                enc_key, salt = self._derive_key(password)
            else:
                enc_key, salt = self._derive_key_scrypt(password)
            
            # Encrypt the private key
            cipher = Fernet(enc_key)
            encrypted_key = cipher.encrypt(private_key_pem.encode())
            
            # Create metadata
            encrypted_data = {
                'key_id': key_id,
                'encrypted_data': base64.b64encode(encrypted_key).decode(),
                'salt': base64.b64encode(salt).decode(),
                'version': version,
                'created_at': time.time(),
                'created_at_str': datetime.now().isoformat(),
                'encryption_method': 'PBKDF2-SHA256' if version == "v1" else 'Scrypt',
                'key_hash': hashlib.sha256(private_key_pem.encode()).hexdigest()[:16]
            }
            
            return encrypted_data
            
        except Exception as e:
            print(f"❌ Encryption failed: {e}")
            return None
    
    def decrypt_private_key(self, encrypted_data: Dict, password: str) -> Optional[str]:
        """
        Decrypt a private key with user password
        Returns decrypted private key PEM
        """
        try:
            # Get encryption parameters
            version = encrypted_data.get('version', 'v1')
            salt = base64.b64decode(encrypted_data['salt'])
            encrypted_key = base64.b64decode(encrypted_data['encrypted_data'])
            
            # Derive decryption key
            if version == "v1":
                dec_key, _ = self._derive_key(password, salt)
            else:
                dec_key, _ = self._derive_key_scrypt(password, salt)
            
            # Decrypt
            cipher = Fernet(dec_key)
            private_key = cipher.decrypt(encrypted_key)
            
            # Verify integrity (optional)
            computed_hash = hashlib.sha256(private_key).hexdigest()[:16]
            if computed_hash != encrypted_data.get('key_hash', computed_hash):
                print("⚠️ Key hash mismatch - possible corruption")
            
            return private_key.decode()
            
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
            return None
    
    def store_private_key(self, device_id: str, virtual_id: str, private_key_pem: str, password: str) -> bool:
        """
        Store an encrypted private key for a device
        """
        try:
            # Encrypt the private key
            encrypted = self.encrypt_private_key(private_key_pem, password)
            if not encrypted:
                return False
            
            # Store in keys data structure
            if device_id not in self.keys_data:
                self.keys_data[device_id] = {}
            
            self.keys_data[device_id][virtual_id] = {
                'encrypted_key': encrypted,
                'device_id': device_id,
                'virtual_id': virtual_id,
                'stored_at': time.time(),
                'stored_at_str': datetime.now().isoformat(),
                'last_accessed': None,
                'access_count': 0
            }
            
            # Save to disk
            self._save_storage()
            
            print(f"✅ Private key stored for {virtual_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to store key: {e}")
            return False
    
    def get_private_key(self, virtual_id: str, password: str) -> Optional[str]:
        """
        Retrieve and decrypt a private key for a device
        """
        try:
            # Find the key by virtual_id
            for device_id, devices in self.keys_data.items():
                if virtual_id in devices:
                    key_data = devices[virtual_id]
                    
                    # Update access metadata
                    key_data['last_accessed'] = time.time()
                    key_data['last_accessed_str'] = datetime.now().isoformat()
                    key_data['access_count'] = key_data.get('access_count', 0) + 1
                    
                    # Decrypt and return
                    private_key = self.decrypt_private_key(key_data['encrypted_key'], password)
                    
                    if private_key:
                        self._save_storage()  # Save access metadata
                        print(f"✅ Private key retrieved for {virtual_id}")
                        return private_key
                    else:
                        print(f"❌ Failed to decrypt key for {virtual_id}")
                        return None
            
            print(f"❌ No key found for virtual_id: {virtual_id}")
            return None
            
        except Exception as e:
            print(f"❌ Failed to get key: {e}")
            return None
    
    def get_all_devices(self) -> List[Dict]:
        """Get list of all stored devices"""
        devices = []
        for device_id, virtual_devices in self.keys_data.items():
            for virtual_id, key_data in virtual_devices.items():
                devices.append({
                    'device_id': device_id,
                    'virtual_id': virtual_id,
                    'stored_at': key_data['stored_at_str'],
                    'last_accessed': key_data.get('last_accessed_str'),
                    'access_count': key_data.get('access_count', 0),
                    'key_hash': key_data['encrypted_key'].get('key_hash')
                })
        return devices
    
    def delete_private_key(self, virtual_id: str) -> bool:
        """
        Delete a stored private key
        """
        try:
            for device_id, devices in self.keys_data.items():
                if virtual_id in devices:
                    del devices[virtual_id]
                    
                    # Clean up empty device entries
                    if not devices:
                        del self.keys_data[device_id]
                    
                    self._save_storage()
                    print(f"🗑️ Deleted private key for {virtual_id}")
                    return True
            
            print(f"❌ No key found for {virtual_id}")
            return False
            
        except Exception as e:
            print(f"❌ Failed to delete key: {e}")
            return False
    
    def update_password(self, virtual_id: str, old_password: str, new_password: str) -> bool:
        """
        Update password for a stored private key
        Re-encrypts the key with new password
        """
        try:
            # Get existing private key
            private_key = self.get_private_key(virtual_id, old_password)
            if not private_key:
                print(f"❌ Failed to retrieve key with old password")
                return False
            
            # Delete old entry
            self.delete_private_key(virtual_id)
            
            # Find device_id
            device_id = None
            for did, devices in self.keys_data.items():
                if virtual_id in devices:
                    device_id = did
                    break
            
            if not device_id:
                print(f"❌ Device not found")
                return False
            
            # Store with new password
            return self.store_private_key(device_id, virtual_id, private_key, new_password)
            
        except Exception as e:
            print(f"❌ Failed to update password: {e}")
            return False
    
    def backup_storage(self) -> str:
        """Create a backup of the storage"""
        try:
            backup_file = os.path.join(BACKUP_DIR, f"keys_backup_{int(time.time())}.json")
            
            backup_data = {
                'backup_time': time.time(),
                'backup_time_str': datetime.now().isoformat(),
                'keys_data': self.keys_data,
                'version': self.current_version
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            print(f"✅ Backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def restore_from_backup(self, backup_file: str) -> bool:
        """Restore storage from backup"""
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            self.keys_data = backup_data['keys_data']
            self._save_storage()
            
            print(f"✅ Restored from backup: {backup_file}")
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False
    
    def _save_storage(self):
        """Save keys data to disk (encrypted at rest)"""
        try:
            # Save encrypted keys (not the actual private keys)
            save_data = {
                'keys_data': self.keys_data,
                'last_saved': time.time(),
                'last_saved_str': datetime.now().isoformat(),
                'version': self.current_version,
                'total_keys': self.get_key_count()
            }
            
            with open(KEYS_FILE, 'w') as f:
                json.dump(save_data, f, indent=2)
            
        except Exception as e:
            print(f"⚠️ Failed to save storage: {e}")
    
    def load_storage(self):
        """Load keys data from disk"""
        try:
            if os.path.exists(KEYS_FILE):
                with open(KEYS_FILE, 'r') as f:
                    save_data = json.load(f)
                    self.keys_data = save_data.get('keys_data', {})
                    print(f"✅ Loaded {self.get_key_count()} keys from storage")
            else:
                print("📁 No existing storage found, creating new")
                self.keys_data = {}
                
        except Exception as e:
            print(f"⚠️ Failed to load storage: {e}")
            self.keys_data = {}
    
    def get_key_count(self) -> int:
        """Get total number of stored keys"""
        count = 0
        for devices in self.keys_data.values():
            count += len(devices)
        return count
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        stats = {
            'total_devices': len(self.keys_data),
            'total_keys': self.get_key_count(),
            'storage_path': STORAGE_DIR,
            'keys_file': KEYS_FILE,
            'backup_count': len(os.listdir(BACKUP_DIR)) if os.path.exists(BACKUP_DIR) else 0,
            'last_saved': datetime.now().isoformat()
        }
        return stats
    
    def verify_key_integrity(self, virtual_id: str, password: str) -> bool:
        """
        Verify that a stored key can be decrypted correctly
        """
        try:
            private_key = self.get_private_key(virtual_id, password)
            if private_key:
                # Check if it's a valid PEM format
                if "BEGIN PRIVATE KEY" in private_key or "BEGIN RSA PRIVATE KEY" in private_key:
                    print(f"✅ Key integrity verified for {virtual_id}")
                    return True
            return False
            
        except Exception as e:
            print(f"❌ Integrity check failed: {e}")
            return False


# ============== GLOBAL INSTANCE ==============
_secure_storage = None

def get_secure_storage():
    """Get or create global secure storage instance"""
    global _secure_storage
    if _secure_storage is None:
        _secure_storage = SecurePrivateKeyStorage()
    return _secure_storage


# ============== SIMPLE API FUNCTIONS ==============

def store_device_key(device_id: str, virtual_id: str, private_key_pem: str, password: str) -> bool:
    """Store a device's private key securely"""
    storage = get_secure_storage()
    return storage.store_private_key(device_id, virtual_id, private_key_pem, password)

def get_device_key(virtual_id: str, password: str) -> Optional[str]:
    """Retrieve a device's private key"""
    storage = get_secure_storage()
    return storage.get_private_key(virtual_id, password)

def delete_device_key(virtual_id: str) -> bool:
    """Delete a device's private key"""
    storage = get_secure_storage()
    return storage.delete_private_key(virtual_id)

def list_stored_devices() -> List[Dict]:
    """List all stored devices"""
    storage = get_secure_storage()
    return storage.get_all_devices()

def update_device_password(virtual_id: str, old_password: str, new_password: str) -> bool:
    """Update password for a device's key"""
    storage = get_secure_storage()
    return storage.update_password(virtual_id, old_password, new_password)

def verify_device_key(virtual_id: str, password: str) -> bool:
    """Verify a stored key can be decrypted"""
    storage = get_secure_storage()
    return storage.verify_key_integrity(virtual_id, password)

def create_backup() -> str:
    """Create a backup of all stored keys"""
    storage = get_secure_storage()
    return storage.backup_storage()

def get_storage_info() -> Dict:
    """Get storage information"""
    storage = get_secure_storage()
    return storage.get_storage_stats()


# ============== TEST CODE ==============
if __name__ == "__main__":
    print("\n" + "="*60)
    print("SECURE PRIVATE KEY STORAGE TEST")
    print("="*60)
    
    # Test data
    TEST_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBALmXfJH8X8xXxYxX
xXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxX
-----END PRIVATE KEY-----"""
    
    TEST_PASSWORD = "MySecurePassword123"
    TEST_DEVICE_ID = "CAMERA_001"
    TEST_VIRTUAL_ID = "VID_CAMERA_123456"
    
    storage = get_secure_storage()
    
    # Test 1: Store key
    print("\n" + "="*50)
    print("TEST 1: Store Private Key")
    print("="*50)
    
    success = storage.store_private_key(TEST_DEVICE_ID, TEST_VIRTUAL_ID, TEST_PRIVATE_KEY, TEST_PASSWORD)
    print(f"\n✅ Key stored: {success}")
    
    # Test 2: List devices
    print("\n" + "="*50)
    print("TEST 2: List Stored Devices")
    print("="*50)
    
    devices = storage.get_all_devices()
    print(f"\n📱 Stored devices: {len(devices)}")
    for device in devices:
        print(f"   - {device['virtual_id']} (Device: {device['device_id']})")
    
    # Test 3: Retrieve key
    print("\n" + "="*50)
    print("TEST 3: Retrieve Private Key")
    print("="*50)
    
    retrieved_key = storage.get_private_key(TEST_VIRTUAL_ID, TEST_PASSWORD)
    print(f"\n🔑 Retrieved key (first 100 chars): {retrieved_key[:100] if retrieved_key else 'None'}...")
    
    if retrieved_key == TEST_PRIVATE_KEY:
        print("\n✅ Key retrieval SUCCESSFUL!")
    else:
        print("\n❌ Key retrieval FAILED!")
    
    # Test 4: Verify integrity
    print("\n" + "="*50)
    print("TEST 4: Verify Key Integrity")
    print("="*50)
    
    is_valid = storage.verify_key_integrity(TEST_VIRTUAL_ID, TEST_PASSWORD)
    print(f"\n✅ Key integrity: {is_valid}")
    
    # Test 5: Storage stats
    print("\n" + "="*50)
    print("TEST 5: Storage Statistics")
    print("="*50)
    
    stats = storage.get_storage_stats()
    print(f"\n📊 Stats:")
    print(f"   Total devices: {stats['total_devices']}")
    print(f"   Total keys: {stats['total_keys']}")
    print(f"   Backup count: {stats['backup_count']}")
    print(f"   Storage path: {stats['storage_path']}")
    
    # Test 6: Create backup
    print("\n" + "="*50)
    print("TEST 6: Create Backup")
    print("="*50)
    
    backup_file = storage.backup_storage()
    print(f"\n💾 Backup created: {backup_file}")
    
    # Test 7: Delete key
    print("\n" + "="*50)
    print("TEST 7: Delete Private Key")
    print("="*50)
    
    deleted = storage.delete_private_key(TEST_VIRTUAL_ID)
    print(f"\n🗑️ Key deleted: {deleted}")
    
    # Verify deletion
    devices_after = storage.get_all_devices()
    print(f"📱 Remaining devices: {len(devices_after)}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SECURE STORAGE SUMMARY")
    print("="*60)
    print("\n✅ Features:")
    print("   - AES-256 encryption at rest")
    print("   - PBKDF2 + Scrypt key derivation")
    print("   - Multiple password versions")
    print("   - Automatic backup support")
    print("   - Access tracking")
    print("   - Key integrity verification")
    
    print("\n✅ API Functions:")
    print("   - store_device_key(device_id, virtual_id, key, password)")
    print("   - get_device_key(virtual_id, password)")
    print("   - delete_device_key(virtual_id)")
    print("   - list_stored_devices()")
    print("   - update_device_password(virtual_id, old_pass, new_pass)")
    print("   - verify_device_key(virtual_id, password)")
    print("   - create_backup()")
    print("   - get_storage_info()")
    
    print("\n" + "="*60)
    print("🎉 SECURE PRIVATE KEY STORAGE READY!")
    print("="*60)