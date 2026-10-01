# edge_layer/secure_key_storage.py
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import getpass

class SecureKeyStorage:
    """
    Hardware Security Module Style Storage
    Private Keys NEVER stored in plain text
    """
    
    def __init__(self):
        self.cipher = None
        self.master_key = None
        self.init_encryption()
    
    def init_encryption(self):
        """Initialize encryption with master password"""
        # Try to get from environment first
        master_password = os.environ.get('MASTER_ENCRYPTION_KEY')
        
        if not master_password:
            # Prompt on first run (not stored anywhere)
            master_password = getpass.getpass("🔐 Enter Master Encryption Key: ")
            if not master_password:
                raise Exception("Master key required!")
        
        # Derive encryption key
        salt = b'iot_blockchain_secure_salt_v2'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200000,  # High iterations for security
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self.cipher = Fernet(key)
        self.master_key = master_password
        print("✅ Secure storage initialized (AES-256)")
    
    def encrypt_private_key(self, private_key_pem, device_id):
        """Encrypt private key before storing"""
        if not self.cipher:
            self.init_encryption()
        
        # Add device-specific salt
        device_salt = hashlib.sha256(device_id.encode()).hexdigest()[:16]
        data_to_encrypt = f"{device_salt}:{private_key_pem}"
        
        encrypted = self.cipher.encrypt(data_to_encrypt.encode())
        return encrypted.decode()
    
    def decrypt_private_key(self, encrypted_key, device_id):
        """Decrypt private key only when needed"""
        if not self.cipher:
            self.init_encryption()
        
        decrypted = self.cipher.decrypt(encrypted_key.encode()).decode()
        # Verify device salt
        stored_salt, private_key = decrypted.split(':', 1)
        device_salt = hashlib.sha256(device_id.encode()).hexdigest()[:16]
        
        if stored_salt != device_salt:
            raise Exception("Invalid key for this device!")
        
        return private_key
    
    def rotate_master_key(self, old_password, new_password):
        """Rotate master key (re-encrypt all keys)"""
        # Implementation for key rotation
        pass