# edge_layer/device_crypto.py - COMPLETE WITH ENCRYPTION/DECRYPTION TESTING
import uuid
import json
import hashlib
import time
import statistics as stat_lib
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
import base64


class DeviceCrypto:
    """Handles cryptographic operations for device registration"""
    
    def __init__(self):
        self.device_keys = {}  # Store keys temporarily (memory only)
        self.key_generation_count = 0
        self.master_key_hash = None  # Store hash of master key (never the key itself)
        
    # ========== OLD METHODS (Keep as is - NO CHANGE) ==========
    
    def generate_key_pair(self, device_id):
        """
        Generate RSA key pair for device
        Returns: (private_key_pem, public_key_pem)
        """
        print(f"🔑 Generating RSA 2048-bit key pair for: {device_id}")
        
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Extract public key
        public_key = private_key.public_key()
        
        # Serialize private key (PEM format)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key (PEM format)
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Store in memory (will be encrypted by edge_gateway)
        self.device_keys[device_id] = {
            'private_key': private_key,
            'public_key': public_key,
            'private_pem': private_pem.decode('utf-8'),
            'public_pem': public_pem.decode('utf-8'),
            'generated_at': time.time()
        }
        
        self.key_generation_count += 1
        
        print(f"   ✅ Key pair generated (Total: {self.key_generation_count})")
        return private_pem.decode('utf-8'), public_pem.decode('utf-8')
    
    def sign_packet(self, device_id, packet_data):
        """
        Sign packet using device's private key
        """
        if device_id not in self.device_keys:
            raise Exception(f"Device {device_id} not found. Generate keys first.")
        
        private_key = self.device_keys[device_id]['private_key']
        
        # Convert packet to JSON string and sign
        packet_json = json.dumps(packet_data, sort_keys=True)
        signature = private_key.sign(
            packet_json.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        return signature.hex()
    
    def verify_signature(self, public_key_pem, packet_data, signature_hex):
        """
        Verify packet signature using public key
        """
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
            
            # Prepare data
            packet_json = json.dumps(packet_data, sort_keys=True)
            signature = bytes.fromhex(signature_hex)
            
            # Verify
            public_key.verify(
                signature,
                packet_json.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return True, "Signature verified"
        except Exception as e:
            return False, f"Verification failed: {str(e)}"
    
    def get_public_key(self, device_id):
        """Get public key for device"""
        if device_id in self.device_keys:
            return self.device_keys[device_id]['public_pem']
        return None
    
    def get_private_key(self, device_id):
        """Get private key for device (for local use only - NEVER sent to network)"""
        if device_id in self.device_keys:
            return self.device_keys[device_id]['private_pem']
        return None
    
    def get_key_generation_stats(self):
        """Get statistics about key generation"""
        return {
            'total_keys_generated': self.key_generation_count,
            'active_keys': len(self.device_keys)
        }
    
    # ========== NEW METHODS (Master Key + Period Number) ==========
    
    def get_period_number(self, timestamp=None):
        """
        Get 6-hour period number from timestamp
        6 hours = 21600 seconds
        Period 0: 00:00-06:00, Period 1: 06:00-12:00, etc.
        """
        if timestamp is None:
            timestamp = time.time()
        
        period_seconds = 6 * 3600  # 21600 seconds
        period_number = int(timestamp // period_seconds)
        
        return period_number
    
    def derive_key_from_master(self, master_key, period_number):
        """
        Derive unique key from master key + period number
        Same master key + same period = same derived key
        """
        salt = f"iot_blockchain_period_{period_number}".encode('utf-8')
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        derived_key = kdf.derive(master_key.encode('utf-8'))
        return base64.urlsafe_b64encode(derived_key)
    
    def encrypt_private_key_with_master(self, private_key_pem, master_key, period_number=None):
        """
        Encrypt private key using master key derived key
        This is for storing private key on blockchain
        """
        if period_number is None:
            period_number = self.get_period_number()
        
        derived_key = self.derive_key_from_master(master_key, period_number)
        cipher = Fernet(derived_key)
        
        encrypted_private_key = cipher.encrypt(private_key_pem.encode('utf-8'))
        
        return {
            'encrypted_private_key': base64.b64encode(encrypted_private_key).decode('utf-8'),
            'period_number': period_number,
            'timestamp': time.time(),
            'encryption_type': 'master_key_hierarchical'
        }
    
    def decrypt_private_key_with_master(self, encrypted_data, master_key):
        """
        Decrypt private key using master key derived key
        Automatically uses period_number from encrypted data
        """
        period_number = encrypted_data.get('period_number')
        
        if period_number is None:
            timestamp = encrypted_data.get('timestamp', time.time())
            period_number = self.get_period_number(timestamp)
        
        derived_key = self.derive_key_from_master(master_key, period_number)
        cipher = Fernet(derived_key)
        
        encrypted_private_key = base64.b64decode(encrypted_data['encrypted_private_key'])
        private_key_pem = cipher.decrypt(encrypted_private_key)
        
        return private_key_pem.decode('utf-8')
    
    def set_master_key_hash(self, master_key):
        """
        Store only the hash of master key (never the key itself)
        Used for verification without storing the actual key
        """
        self.master_key_hash = hashlib.sha256(master_key.encode('utf-8')).hexdigest()
        return self.master_key_hash
    
    def verify_master_key(self, master_key):
        """
        Verify if provided master key matches the stored hash
        """
        if self.master_key_hash is None:
            return True  # No master key set yet
        
        provided_hash = hashlib.sha256(master_key.encode('utf-8')).hexdigest()
        return provided_hash == self.master_key_hash
    
    def encrypt_with_period_key(self, data, master_key, period_number=None):
        """
        Encrypt any data using period-based key
        Generic method for encrypting data with master key
        """
        if period_number is None:
            period_number = self.get_period_number()
        
        derived_key = self.derive_key_from_master(master_key, period_number)
        cipher = Fernet(derived_key)
        
        encrypted_data = cipher.encrypt(data.encode('utf-8') if isinstance(data, str) else data)
        
        return {
            'encrypted_data': base64.b64encode(encrypted_data).decode('utf-8'),
            'period_number': period_number,
            'timestamp': time.time()
        }
    
    def decrypt_with_period_key(self, encrypted_data, master_key):
        """
        Decrypt any data using period-based key
        """
        period_number = encrypted_data.get('period_number')
        
        if period_number is None:
            timestamp = encrypted_data.get('timestamp', time.time())
            period_number = self.get_period_number(timestamp)
        
        derived_key = self.derive_key_from_master(master_key, period_number)
        cipher = Fernet(derived_key)
        
        decrypted_data = base64.b64decode(encrypted_data['encrypted_data'])
        result = cipher.decrypt(decrypted_data)
        
        return result.decode('utf-8') if isinstance(result, bytes) else result
    
    # ========== NEW METHOD: Password-based Decryption for Messages ==========
    
    def decrypt_message_with_private_key(self, encrypted_message, encrypted_key, private_key_pem):
        """
        Decrypt a message using private key
        This is the core decryption function for the EI system
        
        Args:
            encrypted_message: Base64 encoded encrypted message
            encrypted_key: Base64 encoded encrypted symmetric key (RSA encrypted)
            private_key_pem: Private key in PEM format (string)
        
        Returns:
            Decrypted original message (string)
        """
        try:
            print(f"🔓 Decrypting message with private key...")
            
            # Load private key from PEM
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None
            )
            
            # Step 1: Decrypt the symmetric key using RSA private key
            encrypted_key_bytes = base64.b64decode(encrypted_key)
            symmetric_key = private_key.decrypt(
                encrypted_key_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Step 2: Decrypt the message using the symmetric key (Fernet/AES)
            encrypted_message_bytes = base64.b64decode(encrypted_message)
            cipher = Fernet(symmetric_key)
            original_message = cipher.decrypt(encrypted_message_bytes)
            
            print(f"   ✅ Message decrypted successfully")
            return original_message.decode('utf-8')
            
        except Exception as e:
            print(f"   ❌ Decryption failed: {e}")
            raise Exception(f"Failed to decrypt message: {str(e)}")
    
    def encrypt_message_with_public_key(self, message, public_key_pem):
        """
        Encrypt a message using public key (for testing)
        
        Args:
            message: Original message to encrypt
            public_key_pem: Public key in PEM format (string)
        
        Returns:
            (encrypted_message_base64, encrypted_key_base64)
        """
        try:
            print(f"🔒 Encrypting message with public key...")
            
            # Load public key from PEM
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
            
            # Step 1: Generate a random symmetric key (Fernet key)
            symmetric_key = Fernet.generate_key()
            
            # Step 2: Encrypt the message with the symmetric key
            cipher = Fernet(symmetric_key)
            encrypted_message = cipher.encrypt(message.encode('utf-8'))
            
            # Step 3: Encrypt the symmetric key with RSA public key
            encrypted_key = public_key.encrypt(
                symmetric_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            print(f"   ✅ Message encrypted successfully")
            return base64.b64encode(encrypted_message).decode('utf-8'), base64.b64encode(encrypted_key).decode('utf-8')
            
        except Exception as e:
            print(f"   ❌ Encryption failed: {e}")
            raise Exception(f"Failed to encrypt message: {str(e)}")
    
    # ========== ENCRYPTION/DECRYPTION TESTING FUNCTIONS ==========
    
    def test_key_generation_time(self, num_tests=20):
        """
        Test 1: Measure RSA key pair generation time
        """
        generation_times = []
        results = []
        
        for i in range(num_tests):
            device_id = f"TEST_DEVICE_{i}_{int(time.time())}"
            
            start_time = time.perf_counter()
            private_key, public_key = self.generate_key_pair(device_id)
            end_time = time.perf_counter()
            
            generation_time_ms = (end_time - start_time) * 1000
            generation_times.append(generation_time_ms)
            
            results.append({
                'test_number': i + 1,
                'generation_time_ms': round(generation_time_ms, 2),
                'private_key_len': len(private_key),
                'public_key_len': len(public_key)
            })
            
            # Clean up to avoid memory issues
            del self.device_keys[device_id]
            time.sleep(0.05)
        
        return {
            'test_type': 'key_generation_time',
            'total_tests': num_tests,
            'statistics': {
                'average_ms': round(stat_lib.mean(generation_times), 2),
                'min_ms': round(min(generation_times), 2),
                'max_ms': round(max(generation_times), 2),
                'std_dev_ms': round(stat_lib.stdev(generation_times), 2) if len(generation_times) > 1 else 0
            },
            'results': results[:10]  # First 10 results only
        }
    
    def test_encryption_time(self, message_sizes=[64, 256, 1024, 4096, 16384], num_tests=20):
        """
        Test 2: Measure encryption time for different message sizes
        Message sizes in bytes: 64B, 256B, 1KB, 4KB, 16KB
        """
        # Generate a test key pair
        test_device = f"ENCRYPT_TEST_{int(time.time())}"
        private_key, public_key = self.generate_key_pair(test_device)
        
        results = []
        
        for size in message_sizes:
            test_message = "X" * size  # Create message of specified size
            encryption_times = []
            
            for i in range(num_tests):
                start_time = time.perf_counter()
                encrypted_msg, encrypted_key = self.encrypt_message_with_public_key(test_message, public_key)
                end_time = time.perf_counter()
                
                encryption_time_ms = (end_time - start_time) * 1000
                encryption_times.append(encryption_time_ms)
                time.sleep(0.01)
            
            results.append({
                'message_size_bytes': size,
                'message_size_kb': round(size / 1024, 2),
                'average_encryption_time_ms': round(stat_lib.mean(encryption_times), 2),
                'min_encryption_time_ms': round(min(encryption_times), 2),
                'max_encryption_time_ms': round(max(encryption_times), 2),
                'std_dev_ms': round(stat_lib.stdev(encryption_times), 2) if len(encryption_times) > 1 else 0
            })
        
        # Clean up
        del self.device_keys[test_device]
        
        return {
            'test_type': 'encryption_time',
            'message_sizes_tested': len(message_sizes),
            'total_tests_per_size': num_tests,
            'results': results,
            'summary': {
                'average_encryption_time_ms': round(sum(r['average_encryption_time_ms'] for r in results) / len(results), 2) if results else 0,
                'fastest_size': results[results.index(min(results, key=lambda x: x['average_encryption_time_ms']))]['message_size_kb'] if results else 0
            }
        }
    
    def test_decryption_time(self, message_sizes=[64, 256, 1024, 4096, 16384], num_tests=20):
        """
        Test 3: Measure decryption time for different message sizes
        """
        # Generate a test key pair
        test_device = f"DECRYPT_TEST_{int(time.time())}"
        private_key, public_key = self.generate_key_pair(test_device)
        
        results = []
        
        for size in message_sizes:
            test_message = "Y" * size
            decryption_times = []
            
            # Encrypt once to get encrypted data
            encrypted_msg, encrypted_key_enc = self.encrypt_message_with_public_key(test_message, public_key)
            
            for i in range(num_tests):
                start_time = time.perf_counter()
                decrypted = self.decrypt_message_with_private_key(encrypted_msg, encrypted_key_enc, private_key)
                end_time = time.perf_counter()
                
                decryption_time_ms = (end_time - start_time) * 1000
                decryption_times.append(decryption_time_ms)
                time.sleep(0.01)
            
            results.append({
                'message_size_bytes': size,
                'message_size_kb': round(size / 1024, 2),
                'average_decryption_time_ms': round(stat_lib.mean(decryption_times), 2),
                'min_decryption_time_ms': round(min(decryption_times), 2),
                'max_decryption_time_ms': round(max(decryption_times), 2),
                'std_dev_ms': round(stat_lib.stdev(decryption_times), 2) if len(decryption_times) > 1 else 0
            })
        
        # Clean up
        del self.device_keys[test_device]
        
        return {
            'test_type': 'decryption_time',
            'message_sizes_tested': len(message_sizes),
            'total_tests_per_size': num_tests,
            'results': results,
            'summary': {
                'average_decryption_time_ms': round(sum(r['average_decryption_time_ms'] for r in results) / len(results), 2) if results else 0,
                'zero_gas_fee': True,
                'note': 'Decryption happens at Edge Layer - NO GAS FEE!'
            }
        }
    
    def test_encryption_decryption_comparison(self, num_tests=50, message_size=1024):
        """
        Test 4: Compare encryption vs decryption time for same message size
        """
        # Generate a test key pair
        test_device = f"COMPARE_TEST_{int(time.time())}"
        private_key, public_key = self.generate_key_pair(test_device)
        
        test_message = "Z" * message_size
        encryption_times = []
        decryption_times = []
        
        # Pre-encrypt a message for decryption test
        encrypted_msg, encrypted_key_enc = self.encrypt_message_with_public_key(test_message, public_key)
        
        for i in range(num_tests):
            # Encryption time
            start_enc = time.perf_counter()
            enc_msg, enc_key = self.encrypt_message_with_public_key(test_message, public_key)
            end_enc = time.perf_counter()
            encryption_times.append((end_enc - start_enc) * 1000)
            
            # Decryption time
            start_dec = time.perf_counter()
            decrypted = self.decrypt_message_with_private_key(encrypted_msg, encrypted_key_enc, private_key)
            end_dec = time.perf_counter()
            decryption_times.append((end_dec - start_dec) * 1000)
            
            time.sleep(0.05)
        
        # Clean up
        del self.device_keys[test_device]
        
        avg_encryption = stat_lib.mean(encryption_times)
        avg_decryption = stat_lib.mean(decryption_times)
        
        return {
            'test_type': 'encryption_decryption_comparison',
            'message_size_bytes': message_size,
            'message_size_kb': round(message_size / 1024, 2),
            'total_tests': num_tests,
            'encryption': {
                'average_ms': round(avg_encryption, 2),
                'min_ms': round(min(encryption_times), 2),
                'max_ms': round(max(encryption_times), 2),
                'std_dev_ms': round(stat_lib.stdev(encryption_times), 2) if len(encryption_times) > 1 else 0
            },
            'decryption': {
                'average_ms': round(avg_decryption, 2),
                'min_ms': round(min(decryption_times), 2),
                'max_ms': round(max(decryption_times), 2),
                'std_dev_ms': round(stat_lib.stdev(decryption_times), 2) if len(decryption_times) > 1 else 0,
                'zero_gas_fee': True
            },
            'ratio': {
                'encryption_vs_decryption': round(avg_encryption / avg_decryption, 2),
                'faster_operation': 'encryption' if avg_encryption < avg_decryption else 'decryption'
            }
        }
    
    def test_rsa_key_sizes(self):
        """
        Test 5: Compare key sizes for different key types
        """
        test_device = f"KEY_SIZE_TEST_{int(time.time())}"
        private_key, public_key = self.generate_key_pair(test_device)
        
        # Get key sizes
        private_key_size = len(private_key.encode('utf-8'))
        public_key_size = len(public_key.encode('utf-8'))
        
        # Clean up
        del self.device_keys[test_device]
        
        return {
            'test_type': 'rsa_key_sizes',
            'private_key_bytes': private_key_size,
            'private_key_kb': round(private_key_size / 1024, 2),
            'public_key_bytes': public_key_size,
            'public_key_kb': round(public_key_size / 1024, 2),
            'total_keys_stored': self.key_generation_count,
            'key_type': 'RSA-2048'
        }
    
    def test_signature_generation_time(self, num_tests=30):
        """
        Test 6: Measure signature generation time
        """
        # Generate a test key pair
        test_device = f"SIGN_TEST_{int(time.time())}"
        private_key, public_key = self.generate_key_pair(test_device)
        
        test_data = {
            'device_id': test_device,
            'timestamp': time.time(),
            'data': 'Test signature data'
        }
        
        signature_times = []
        
        for i in range(num_tests):
            start_time = time.perf_counter()
            signature = self.sign_packet(test_device, test_data)
            end_time = time.perf_counter()
            
            signature_time_ms = (end_time - start_time) * 1000
            signature_times.append(signature_time_ms)
            time.sleep(0.05)
        
        # Verify signature time
        start_verify = time.perf_counter()
        is_valid, msg = self.verify_signature(public_key, test_data, signature)
        end_verify = time.perf_counter()
        verification_time_ms = (end_verify - start_verify) * 1000
        
        # Clean up
        del self.device_keys[test_device]
        
        return {
            'test_type': 'signature_performance',
            'total_tests': num_tests,
            'signature_generation': {
                'average_ms': round(stat_lib.mean(signature_times), 2),
                'min_ms': round(min(signature_times), 2),
                'max_ms': round(max(signature_times), 2),
                'std_dev_ms': round(stat_lib.stdev(signature_times), 2) if len(signature_times) > 1 else 0
            },
            'signature_verification_time_ms': round(verification_time_ms, 2),
            'signature_valid': is_valid,
            'signature_length': len(signature)
        }
    
    def run_all_crypto_tests(self):
        """
        Run all encryption/decryption performance tests
        """
        print("\n" + "="*60)
        print("🧪 Running Encryption/Decryption Performance Tests")
        print("="*60)
        
        results = {
            'key_generation': self.test_key_generation_time(15),
            'encryption_time': self.test_encryption_time(num_tests=10),
            'decryption_time': self.test_decryption_time(num_tests=10),
            'encryption_decryption_comparison': self.test_encryption_decryption_comparison(20, 1024),
            'rsa_key_sizes': self.test_rsa_key_sizes(),
            'signature_performance': self.test_signature_generation_time(15),
            'timestamp': time.time(),
            'zero_gas_fee_note': 'All decryption operations happen at Edge Layer - NO BLOCKCHAIN GAS FEE!'
        }
        
        print("\n✅ All crypto tests completed!")
        return results
    
    def get_crypto_metrics(self):
        """
        Get all crypto performance metrics summary
        """
        key_gen = self.test_key_generation_time(10)
        enc_test = self.test_encryption_time(num_tests=5)
        dec_test = self.test_decryption_time(num_tests=5)
        
        return {
            'avg_key_generation_time_ms': key_gen['statistics']['average_ms'],
            'avg_encryption_time_1KB_ms': next((r['average_encryption_time_ms'] for r in enc_test['results'] if r['message_size_kb'] == 1), 0),
            'avg_decryption_time_1KB_ms': next((r['average_decryption_time_ms'] for r in dec_test['results'] if r['message_size_kb'] == 1), 0),
            'total_keys_generated': self.key_generation_count,
            'zero_gas_fee': True,
            'encryption_algorithm': 'RSA-2048 + AES-256 (Fernet)'
        }


# ========== TEST CODE ==========
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing DeviceCrypto (RSA + Master Key + Message Decryption)")
    print("="*60)
    
    crypto = DeviceCrypto()
    
    # ========== TEST 1: RSA Key Generation (Old) ==========
    print("\n" + "="*50)
    print("TEST 1: RSA Key Generation")
    print("="*50)
    
    device_id = "TEST_DEVICE_001"
    private_key, public_key = crypto.generate_key_pair(device_id)
    
    print(f"\n✅ Device ID: {device_id}")
    print(f"✅ Private Key (first 50 chars): {private_key[:50]}...")
    print(f"✅ Public Key (first 50 chars): {public_key[:50]}...")
    
    # ========== TEST 2: Message Encryption/Decryption (NEW) ==========
    print("\n" + "="*50)
    print("TEST 2: Message Encryption/Decryption (NEW METHOD)")
    print("="*50)
    
    original_message = "Hello World! This is a secret message from IoT device."
    print(f"\n📝 Original Message: {original_message}")
    
    # Encrypt with public key
    encrypted_msg, encrypted_key = crypto.encrypt_message_with_public_key(original_message, public_key)
    print(f"\n🔒 Encrypted Message: {encrypted_msg[:50]}...")
    print(f"🔑 Encrypted Key: {encrypted_key[:50]}...")
    
    # Decrypt with private key (NEW METHOD)
    decrypted_message = crypto.decrypt_message_with_private_key(encrypted_msg, encrypted_key, private_key)
    print(f"\n🔓 Decrypted Message: {decrypted_message}")
    
    if decrypted_message == original_message:
        print("\n✅ Message encryption/decryption WORKING!")
    else:
        print("\n❌ Message encryption/decryption FAILED!")
    
    # ========== TEST 3: Master Key Encryption ==========
    print("\n" + "="*50)
    print("TEST 3: Master Key Encryption")
    print("="*50)
    
    MASTER_KEY = "MySecretMasterKey123"
    
    # Encrypt private key with master key
    print(f"\n🔑 Master Key: {MASTER_KEY}")
    print(f"📅 Current Period: {crypto.get_period_number()}")
    
    encrypted_result = crypto.encrypt_private_key_with_master(private_key, MASTER_KEY)
    print(f"\n🔒 Encrypted Private Key: {encrypted_result['encrypted_private_key'][:50]}...")
    print(f"   Period: {encrypted_result['period_number']}")
    
    # Decrypt private key with master key
    decrypted_key = crypto.decrypt_private_key_with_master(encrypted_result, MASTER_KEY)
    print(f"\n🔓 Decrypted Private Key (first 50 chars): {decrypted_key[:50]}...")
    
    if decrypted_key == private_key:
        print("\n✅ Master key encryption/decryption WORKING!")
    else:
        print("\n❌ Master key encryption/decryption FAILED!")
    
    # ========== TEST 4: Master Key Hash (Security) ==========
    print("\n" + "="*50)
    print("TEST 4: Master Key Hash (No Key Storage)")
    print("="*50)
    
    crypto.set_master_key_hash(MASTER_KEY)
    print(f"\n🔐 Master Key Hash: {crypto.master_key_hash}")
    
    # Verify correct key
    is_valid = crypto.verify_master_key(MASTER_KEY)
    print(f"✅ Correct master key verification: {is_valid}")
    
    # Verify wrong key
    is_valid = crypto.verify_master_key("WrongKey123")
    print(f"❌ Wrong master key verification: {is_valid}")
    
    # ========== TEST 5: Different Periods = Different Keys ==========
    print("\n" + "="*50)
    print("TEST 5: Different Periods = Different Keys")
    print("="*50)
    
    period_1 = 1000
    period_2 = 1001
    
    key1 = crypto.derive_key_from_master(MASTER_KEY, period_1)
    key2 = crypto.derive_key_from_master(MASTER_KEY, period_2)
    
    print(f"\n🔑 Key for period {period_1}: {key1[:20]}...")
    print(f"🔑 Key for period {period_2}: {key2[:20]}...")
    
    if key1 != key2:
        print("\n✅ Different periods produce DIFFERENT keys!")
    else:
        print("\n❌ Different periods produced SAME keys!")
    
    # ========== TEST 6: Same Period = Same Key ==========
    print("\n" + "="*50)
    print("TEST 6: Same Period = Same Key")
    print("="*50)
    
    key1_same = crypto.derive_key_from_master(MASTER_KEY, period_1)
    key2_same = crypto.derive_key_from_master(MASTER_KEY, period_1)
    
    if key1_same == key2_same:
        print("\n✅ Same period produces SAME key! (Can decrypt old messages)")
    else:
        print("\n❌ Same period produced DIFFERENT keys!")
    
    # ========== RUN ALL PERFORMANCE TESTS ==========
    print("\n" + "="*60)
    print("RUNNING ALL ENCRYPTION/DECRYPTION PERFORMANCE TESTS")
    print("="*60)
    
    perf_results = crypto.run_all_crypto_tests()
    
    # ========== SUMMARY ==========
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print("\n✅ OLD METHODS (Keep as is):")
    print("   - generate_key_pair()")
    print("   - sign_packet()")
    print("   - verify_signature()")
    print("   - get_public_key()")
    print("   - get_private_key()")
    print("   - get_key_generation_stats()")
    
    print("\n✅ EXISTING NEW METHODS (Unchanged):")
    print("   - get_period_number()")
    print("   - derive_key_from_master()")
    print("   - encrypt_private_key_with_master()")
    print("   - decrypt_private_key_with_master()")
    print("   - set_master_key_hash()")
    print("   - verify_master_key()")
    print("   - encrypt_with_period_key()")
    print("   - decrypt_with_period_key()")
    
    print("\n✅ NEW METHODS ADDED (For EI System):")
    print("   - decrypt_message_with_private_key() ← MAIN DECRYPTION")
    print("   - encrypt_message_with_public_key() ← FOR TESTING")
    
    print("\n✅ NEW TESTING METHODS ADDED:")
    print("   - test_key_generation_time()")
    print("   - test_encryption_time()")
    print("   - test_decryption_time()")
    print("   - test_encryption_decryption_comparison()")
    print("   - test_rsa_key_sizes()")
    print("   - test_signature_generation_time()")
    print("   - run_all_crypto_tests()")
    print("   - get_crypto_metrics()")
    
    print("\n🔐 Security Features:")
    print("   - RSA keys: Device to Device encryption")
    print("   - Master key: NEVER stored (only hash)")
    print("   - Period-based keys: Auto-rotate every 6 hours")
    print("   - Old messages: Still accessible")
    print("   - Hybrid encryption: RSA + AES (Fernet)")
    print("   - Zero Gas Fee Decryption at Edge Layer!")
    
    print("\n📊 Performance Results Summary:")
    print(f"   Key Generation Avg: {perf_results['key_generation']['statistics']['average_ms']} ms")
    print(f"   Encryption Avg (1KB): {next((r['average_encryption_time_ms'] for r in perf_results['encryption_time']['results'] if r['message_size_kb'] == 1), 0)} ms")
    print(f"   Decryption Avg (1KB): {next((r['average_decryption_time_ms'] for r in perf_results['decryption_time']['results'] if r['message_size_kb'] == 1), 0)} ms")
    
    print("\n" + "="*60)
    print("🎉 DeviceCrypto UPDATE COMPLETE!")
    print("="*60)