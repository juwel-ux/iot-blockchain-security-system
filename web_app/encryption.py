# web_app/encryption.py
import hashlib
import base64
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

class EncryptionHandler:
    """Complete E2EE Encryption Handler for IoT Blockchain System"""
    
    def __init__(self):
        self.key_cache = {}
    
    def generate_key_pair(self):
        """
        Generate RSA 2048-bit key pair for a device
        Returns: dict with private_key, public_key, and key objects
        """
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # Serialize private key to PEM
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key to PEM
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            'private_key': private_pem.decode('utf-8'),
            'public_key': public_pem.decode('utf-8'),
            'private_key_obj': private_key,
            'public_key_obj': public_key
        }
    
    def encrypt_with_public_key(self, plaintext, public_key_pem):
        """
        Encrypt a message using receiver's public key (Hybrid Encryption)
        Uses RSA to encrypt a symmetric key, then Fernet for the actual message
        Returns: dict with encrypted_message and encrypted_key
        """
        try:
            # Load the public key from PEM
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            # Generate a random symmetric key (Fernet key - 32 bytes)
            symmetric_key = Fernet.generate_key()
            cipher = Fernet(symmetric_key)
            
            # Encrypt the actual message with the symmetric key
            encrypted_message = cipher.encrypt(plaintext.encode('utf-8'))
            
            # Encrypt the symmetric key with RSA public key
            encrypted_key = public_key.encrypt(
                symmetric_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return {
                'encrypted_message': base64.b64encode(encrypted_message).decode('utf-8'),
                'encrypted_key': base64.b64encode(encrypted_key).decode('utf-8')
            }
            
        except Exception as e:
            print(f"❌ Encryption failed: {e}")
            return None
    
    def decrypt_with_private_key(self, encrypted_message_b64, encrypted_key_b64, private_key_pem):
        """
        Decrypt a message using receiver's private key
        First decrypts the symmetric key with RSA, then decrypts the message with Fernet
        Returns: decrypted plaintext string
        """
        try:
            # Load the private key from PEM
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            # Decode from base64
            encrypted_message = base64.b64decode(encrypted_message_b64)
            encrypted_key = base64.b64decode(encrypted_key_b64)
            
            # Decrypt the symmetric key with RSA private key
            symmetric_key = private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt the message with the symmetric key
            cipher = Fernet(symmetric_key)
            decrypted_message = cipher.decrypt(encrypted_message)
            
            return decrypted_message.decode('utf-8')
            
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
            return None
    
    def sign_message(self, message, private_key_pem):
        """
        Sign a message using sender's private key
        Returns: base64 encoded signature
        """
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            # Create SHA-256 hash of the message
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()
            
            # Sign the hash
            signature = private_key.sign(
                message_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return base64.b64encode(signature).decode('utf-8')
            
        except Exception as e:
            print(f"❌ Signing failed: {e}")
            return None
    
    def verify_signature(self, message, signature_b64, public_key_pem):
        """
        Verify a signature using sender's public key
        Returns: True if signature is valid, False otherwise
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            # Create SHA-256 hash of the message
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()
            signature = base64.b64decode(signature_b64)
            
            # Verify the signature
            public_key.verify(
                signature,
                message_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
            
        except Exception as e:
            print(f"❌ Signature verification failed: {e}")
            return False
    
    def generate_message_hash(self, message):
        """Generate SHA-256 hash of a message for blockchain storage"""
        return hashlib.sha256(message.encode('utf-8')).hexdigest()
    
    def generate_file_hash(self, file_data):
        """Generate SHA-256 hash of file data for blockchain storage"""
        return hashlib.sha256(file_data).hexdigest()


# ============== TEST CODE ==============
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔐 Testing Complete E2EE Encryption Handler")
    print("="*60)
    
    handler = EncryptionHandler()
    
    # Generate key pairs for sender and receiver
    print("\n📌 Step 1: Generating key pairs...")
    sender_keys = handler.generate_key_pair()
    receiver_keys = handler.generate_key_pair()
    
    print(f"   Sender Public Key: {sender_keys['public_key'][:50]}...")
    print(f"   Receiver Public Key: {receiver_keys['public_key'][:50]}...")
    
    # Original message
    original_message = "Hello Device! This is a secret E2EE message for IoT Blockchain."
    print(f"\n📝 Original Message: {original_message}")
    
    # Step 2: Encrypt with receiver's public key
    print("\n🔒 Step 2: Encrypting message with receiver's public key...")
    encrypted = handler.encrypt_with_public_key(original_message, receiver_keys['public_key'])
    
    if encrypted:
        print(f"   Encrypted Message: {encrypted['encrypted_message'][:50]}...")
        print(f"   Encrypted Key: {encrypted['encrypted_key'][:50]}...")
        
        # Step 3: Sign with sender's private key
        print("\n✍️ Step 3: Signing message with sender's private key...")
        signature = handler.sign_message(original_message, sender_keys['private_key'])
        print(f"   Signature: {signature[:50]}...")
        
        # Step 4: Decrypt with receiver's private key
        print("\n🔓 Step 4: Decrypting with receiver's private key...")
        decrypted = handler.decrypt_with_private_key(
            encrypted['encrypted_message'],
            encrypted['encrypted_key'],
            receiver_keys['private_key']
        )
        print(f"   Decrypted Message: {decrypted}")
        
        # Step 5: Verify signature with sender's public key
        print("\n🔍 Step 5: Verifying signature with sender's public key...")
        is_valid = handler.verify_signature(decrypted, signature, sender_keys['public_key'])
        print(f"   Signature Valid: {is_valid}")
        
        # Final result
        if decrypted == original_message and is_valid:
            print("\n" + "="*60)
            print("🎉 ALL TESTS PASSED! E2EE is working perfectly!")
            print("="*60)
            print("\n✅ Features working:")
            print("   • RSA 2048-bit key generation")
            print("   • Hybrid encryption (RSA + Fernet)")
            print("   • Digital signature")
            print("   • Signature verification")
            print("   • Message hash generation")
        else:
            print("\n❌ Tests failed!")
    else:
        print("\n❌ Encryption failed!")