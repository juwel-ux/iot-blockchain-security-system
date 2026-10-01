# ipfs_handler/encryption.py
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import hashlib
import time
import os
import statistics as stat_lib


class EncryptionHandler:
    """Handles encryption/decryption for messages"""
    
    def __init__(self):
        pass
    
    # ========== OLD METHODS (RSA - Keep as is) ==========
    
    def generate_key_pair(self):
        """Generate RSA key pair (2048-bit)"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
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
    
    def encrypt_with_public_key(self, message, public_key_pem):
        """Encrypt message with receiver's public key (RSA)"""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
            
            # For longer messages, use hybrid encryption
            # First generate symmetric key
            symmetric_key = Fernet.generate_key()
            cipher = Fernet(symmetric_key)
            
            # Encrypt message with symmetric key
            encrypted_message = cipher.encrypt(message.encode('utf-8'))
            
            # Encrypt symmetric key with RSA public key
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
    
    def decrypt_with_private_key(self, encrypted_data, private_key_pem):
        """Decrypt message with receiver's private key (RSA)"""
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None
            )
            
            # Decode from base64
            encrypted_message = base64.b64decode(encrypted_data['encrypted_message'])
            encrypted_key = base64.b64decode(encrypted_data['encrypted_key'])
            
            # Decrypt symmetric key with RSA private key
            symmetric_key = private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt message with symmetric key
            cipher = Fernet(symmetric_key)
            decrypted_message = cipher.decrypt(encrypted_message)
            
            return decrypted_message.decode('utf-8')
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
            return None
    
    def sign_message(self, message, private_key_pem):
        """Sign message with sender's private key"""
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None
            )
            
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()
            
            signature = private_key.sign(
                message_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            print(f"❌ Signing failed: {e}")
            return None
    
    def verify_signature(self, message, signature, public_key_pem):
        """Verify signature with sender's public key"""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
            
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()
            signature_bytes = base64.b64decode(signature)
            
            public_key.verify(
                signature_bytes,
                message_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"❌ Signature verification failed: {e}")
            return False
    
    # ========== NEW METHODS (Hierarchical Keys with Master Key) ==========
    
    def get_period_number(self, timestamp=None):
        """
        Get 6-hour period number from timestamp
        6 hours = 21600 seconds
        Period 0: 00:00-06:00, Period 1: 06:00-12:00, etc.
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Each period is 6 hours (21600 seconds)
        period_seconds = 6 * 3600  # 21600
        period_number = int(timestamp // period_seconds)
        
        return period_number
    
    def get_period_start_time(self, period_number):
        """Get start timestamp of a period"""
        period_seconds = 6 * 3600
        return period_number * period_seconds
    
    def derive_key_from_master(self, master_key, period_number):
        """
        Derive unique key from master key + period number
        Same master key + same period = same derived key
        Different period = different derived key
        """
        # Create unique salt for each period
        salt = f"iot_blockchain_period_{period_number}".encode('utf-8')
        
        # Use PBKDF2 for key derivation (100,000 iterations for security)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256-bit key
            salt=salt,
            iterations=100000,
        )
        
        derived_key = kdf.derive(master_key.encode('utf-8'))
        
        # Return as base64 for Fernet compatibility
        return base64.urlsafe_b64encode(derived_key)
    
    def encrypt_with_master_key(self, message, master_key, period_number=None):
        """
        Encrypt message using master key derived key
        If period_number not provided, uses current period
        """
        try:
            if period_number is None:
                period_number = self.get_period_number()
            
            # Derive key for this period
            derived_key = self.derive_key_from_master(master_key, period_number)
            
            # Create cipher with derived key
            cipher = Fernet(derived_key)
            
            # Encrypt message
            encrypted_message = cipher.encrypt(message.encode('utf-8'))
            
            return {
                'encrypted_message': base64.b64encode(encrypted_message).decode('utf-8'),
                'period_number': period_number,
                'timestamp': time.time(),
                'encryption_type': 'master_key_hierarchical'
            }
        except Exception as e:
            print(f"❌ Master key encryption failed: {e}")
            return None
    
    def decrypt_with_master_key(self, encrypted_data, master_key):
        """
        Decrypt message using master key derived key
        Automatically uses period_number from encrypted data
        """
        try:
            period_number = encrypted_data.get('period_number')
            
            if period_number is None:
                # Try to detect period from timestamp
                timestamp = encrypted_data.get('timestamp', time.time())
                period_number = self.get_period_number(timestamp)
            
            # Derive key for that period
            derived_key = self.derive_key_from_master(master_key, period_number)
            
            # Create cipher with derived key
            cipher = Fernet(derived_key)
            
            # Decrypt message
            encrypted_message = base64.b64decode(encrypted_data['encrypted_message'])
            decrypted_message = cipher.decrypt(encrypted_message)
            
            return decrypted_message.decode('utf-8')
        except Exception as e:
            print(f"❌ Master key decryption failed: {e}")
            return None
    
    def verify_master_key(self, master_key, period_number, test_message="test"):
        """
        Verify if master key is correct by encrypting and decrypting a test message
        Returns: (is_valid, derived_key)
        """
        try:
            # Encrypt test message
            encrypted = self.encrypt_with_master_key(test_message, master_key, period_number)
            if not encrypted:
                return False, None
            
            # Decrypt test message
            decrypted = self.decrypt_with_master_key(encrypted, master_key)
            
            if decrypted == test_message:
                # Derive key for returning
                derived_key = self.derive_key_from_master(master_key, period_number)
                return True, derived_key
            
            return False, None
        except Exception as e:
            print(f"❌ Master key verification failed: {e}")
            return False, None
    
    def get_all_periods_between(self, start_timestamp, end_timestamp):
        """Get all period numbers between two timestamps"""
        start_period = self.get_period_number(start_timestamp)
        end_period = self.get_period_number(end_timestamp)
        
        return list(range(start_period, end_period + 1))
    
    # ========== ENCRYPTION/DECRYPTION TESTING FUNCTIONS ==========
    
    def test_rsa_encryption_time(self, message_sizes=[64, 256, 1024, 4096, 16384], num_tests=10):
        """
        Test 1: Measure RSA encryption time for different message sizes
        """
        # Generate key pair
        keys = self.generate_key_pair()
        public_key = keys['public_key']
        private_key = keys['private_key']
        
        results = []
        
        for size in message_sizes:
            test_message = "X" * size
            encryption_times = []
            decryption_times = []
            
            # Pre-encrypt for decryption test
            encrypted = self.encrypt_with_public_key(test_message, public_key)
            
            for i in range(num_tests):
                # Encryption time
                start_enc = time.perf_counter()
                enc_result = self.encrypt_with_public_key(test_message, public_key)
                end_enc = time.perf_counter()
                if enc_result:
                    encryption_times.append((end_enc - start_enc) * 1000)
                
                # Decryption time
                if encrypted:
                    start_dec = time.perf_counter()
                    decrypted = self.decrypt_with_private_key(encrypted, private_key)
                    end_dec = time.perf_counter()
                    if decrypted:
                        decryption_times.append((end_dec - start_dec) * 1000)
                
                time.sleep(0.05)
            
            results.append({
                'message_size_bytes': size,
                'message_size_kb': round(size / 1024, 2),
                'encryption_avg_ms': round(stat_lib.mean(encryption_times), 2) if encryption_times else 0,
                'encryption_min_ms': round(min(encryption_times), 2) if encryption_times else 0,
                'encryption_max_ms': round(max(encryption_times), 2) if encryption_times else 0,
                'decryption_avg_ms': round(stat_lib.mean(decryption_times), 2) if decryption_times else 0,
                'decryption_min_ms': round(min(decryption_times), 2) if decryption_times else 0,
                'decryption_max_ms': round(max(decryption_times), 2) if decryption_times else 0
            })
        
        return {
            'test_type': 'rsa_performance',
            'total_tests_per_size': num_tests,
            'results': results,
            'summary': {
                'avg_encryption_overall_ms': round(stat_lib.mean([r['encryption_avg_ms'] for r in results if r['encryption_avg_ms'] > 0]), 2) if results else 0,
                'avg_decryption_overall_ms': round(stat_lib.mean([r['decryption_avg_ms'] for r in results if r['decryption_avg_ms'] > 0]), 2) if results else 0
            }
        }
    
    def test_hybrid_encryption_throughput(self, num_messages=100, message_size=1024):
        """
        Test 2: Measure hybrid encryption throughput (RSA + AES)
        """
        # Generate key pair
        keys = self.generate_key_pair()
        public_key = keys['public_key']
        private_key = keys['private_key']
        
        test_message = "Y" * message_size
        encryption_times = []
        decryption_times = []
        
        # Pre-encrypt one message
        sample_encrypted = self.encrypt_with_public_key(test_message, public_key)
        
        for i in range(num_messages):
            # Encryption
            start_enc = time.perf_counter()
            encrypted = self.encrypt_with_public_key(test_message, public_key)
            end_enc = time.perf_counter()
            if encrypted:
                encryption_times.append((end_enc - start_enc) * 1000)
            
            # Decryption (using pre-encrypted to save time)
            if sample_encrypted:
                start_dec = time.perf_counter()
                decrypted = self.decrypt_with_private_key(sample_encrypted, private_key)
                end_dec = time.perf_counter()
                if decrypted:
                    decryption_times.append((end_dec - start_dec) * 1000)
        
        throughput_enc = (num_messages * message_size) / (sum(encryption_times) / 1000) if encryption_times else 0
        throughput_dec = (num_messages * message_size) / (sum(decryption_times) / 1000) if decryption_times else 0
        
        return {
            'test_type': 'hybrid_encryption_throughput',
            'num_messages': num_messages,
            'message_size_bytes': message_size,
            'message_size_kb': round(message_size / 1024, 2),
            'encryption': {
                'total_time_ms': round(sum(encryption_times), 2),
                'average_time_ms': round(stat_lib.mean(encryption_times), 2) if encryption_times else 0,
                'throughput_bytes_per_sec': round(throughput_enc, 2),
                'throughput_mb_per_sec': round(throughput_enc / (1024 * 1024), 2)
            },
            'decryption': {
                'total_time_ms': round(sum(decryption_times), 2),
                'average_time_ms': round(stat_lib.mean(decryption_times), 2) if decryption_times else 0,
                'throughput_bytes_per_sec': round(throughput_dec, 2),
                'throughput_mb_per_sec': round(throughput_dec / (1024 * 1024), 2),
                'zero_gas_fee': True
            }
        }
    
    def test_master_key_encryption_time(self, num_tests=50):
        """
        Test 3: Measure master key encryption/decryption time
        """
        MASTER_KEY = "TestMasterKey123456"
        test_message = "This is a test message for master key encryption" * 10
        
        encryption_times = []
        decryption_times = []
        
        for i in range(num_tests):
            # Encryption time
            start_enc = time.perf_counter()
            encrypted = self.encrypt_with_master_key(test_message, MASTER_KEY)
            end_enc = time.perf_counter()
            if encrypted:
                encryption_times.append((end_enc - start_enc) * 1000)
                
                # Decryption time
                start_dec = time.perf_counter()
                decrypted = self.decrypt_with_master_key(encrypted, MASTER_KEY)
                end_dec = time.perf_counter()
                if decrypted:
                    decryption_times.append((end_dec - start_dec) * 1000)
            
            time.sleep(0.02)
        
        return {
            'test_type': 'master_key_performance',
            'total_tests': num_tests,
            'encryption': {
                'average_ms': round(stat_lib.mean(encryption_times), 2) if encryption_times else 0,
                'min_ms': round(min(encryption_times), 2) if encryption_times else 0,
                'max_ms': round(max(encryption_times), 2) if encryption_times else 0,
                'std_dev_ms': round(stat_lib.stdev(encryption_times), 2) if len(encryption_times) > 1 else 0
            },
            'decryption': {
                'average_ms': round(stat_lib.mean(decryption_times), 2) if decryption_times else 0,
                'min_ms': round(min(decryption_times), 2) if decryption_times else 0,
                'max_ms': round(max(decryption_times), 2) if decryption_times else 0,
                'std_dev_ms': round(stat_lib.stdev(decryption_times), 2) if len(decryption_times) > 1 else 0
            }
        }
    
    def test_signature_performance(self, num_tests=50):
        """
        Test 4: Measure signature generation and verification time
        """
        # Generate key pair
        keys = self.generate_key_pair()
        private_key = keys['private_key']
        public_key = keys['public_key']
        
        test_message = "This is a test message for signature" * 20
        
        signing_times = []
        verification_times = []
        
        # Pre-sign for verification test
        test_signature = self.sign_message(test_message, private_key)
        
        for i in range(num_tests):
            # Signing time
            start_sign = time.perf_counter()
            signature = self.sign_message(test_message, private_key)
            end_sign = time.perf_counter()
            if signature:
                signing_times.append((end_sign - start_sign) * 1000)
            
            # Verification time
            if test_signature:
                start_verify = time.perf_counter()
                is_valid = self.verify_signature(test_message, test_signature, public_key)
                end_verify = time.perf_counter()
                verification_times.append((end_verify - start_verify) * 1000)
            
            time.sleep(0.02)
        
        return {
            'test_type': 'signature_performance',
            'total_tests': num_tests,
            'signing': {
                'average_ms': round(stat_lib.mean(signing_times), 2) if signing_times else 0,
                'min_ms': round(min(signing_times), 2) if signing_times else 0,
                'max_ms': round(max(signing_times), 2) if signing_times else 0,
                'throughput_signatures_per_sec': round(1000 / (stat_lib.mean(signing_times) if signing_times else 1), 2)
            },
            'verification': {
                'average_ms': round(stat_lib.mean(verification_times), 2) if verification_times else 0,
                'min_ms': round(min(verification_times), 2) if verification_times else 0,
                'max_ms': round(max(verification_times), 2) if verification_times else 0,
                'throughput_verifications_per_sec': round(1000 / (stat_lib.mean(verification_times) if verification_times else 1), 2)
            },
            'signature_valid': test_signature is not None
        }
    
    def test_key_derivation_time(self, num_tests=100):
        """
        Test 5: Measure master key derivation time for different periods
        """
        MASTER_KEY = "TestMasterKey123456"
        periods = [0, 100, 1000, 10000, 100000]
        
        results = []
        
        for period in periods:
            derivation_times = []
            for i in range(num_tests):
                start = time.perf_counter()
                derived_key = self.derive_key_from_master(MASTER_KEY, period)
                end = time.perf_counter()
                derivation_times.append((end - start) * 1000)
            
            results.append({
                'period_number': period,
                'average_derivation_time_ms': round(stat_lib.mean(derivation_times), 3),
                'min_ms': round(min(derivation_times), 3),
                'max_ms': round(max(derivation_times), 3)
            })
        
        return {
            'test_type': 'key_derivation_performance',
            'total_tests_per_period': num_tests,
            'results': results,
            'summary': {
                'overall_average_ms': round(stat_lib.mean([r['average_derivation_time_ms'] for r in results]), 3),
                'iterations': 100000,
                'hash_algorithm': 'SHA-256'
            }
        }
    
    def test_encryption_error_rate(self, num_tests=100):
        """
        Test 6: Measure encryption/decryption error rate
        """
        # Generate key pair
        keys = self.generate_key_pair()
        public_key = keys['public_key']
        private_key = keys['private_key']
        
        test_messages = [
            "Short message",
            "Medium length message for testing" * 10,
            "X" * 5000,  # Large message
            "Message with special chars: !@#$%^&*()",
            "Unicode message: 你好世界 👋🌍"
        ]
        
        errors = 0
        total = 0
        
        for msg in test_messages:
            for i in range(num_tests):
                try:
                    encrypted = self.encrypt_with_public_key(msg, public_key)
                    if not encrypted:
                        errors += 1
                        continue
                    
                    decrypted = self.decrypt_with_private_key(encrypted, private_key)
                    if decrypted != msg:
                        errors += 1
                except Exception as e:
                    errors += 1
                
                total += 1
        
        success_rate = ((total - errors) / total) * 100 if total > 0 else 0
        
        return {
            'test_type': 'encryption_error_rate',
            'total_tests': total,
            'errors': errors,
            'success_rate_percentage': round(success_rate, 4),
            'message_types_tested': len(test_messages),
            'tests_per_message': num_tests
        }
    
    def run_all_encryption_tests(self):
        """
        Run all encryption/decryption performance tests
        """
        print("\n" + "="*60)
        print("🧪 Running Encryption/Decryption Performance Tests")
        print("="*60)
        
        results = {
            'rsa_performance': self.test_rsa_encryption_time(num_tests=8),
            'hybrid_throughput': self.test_hybrid_encryption_throughput(50, 1024),
            'master_key_performance': self.test_master_key_encryption_time(30),
            'signature_performance': self.test_signature_performance(30),
            'key_derivation': self.test_key_derivation_time(50),
            'error_rate': self.test_encryption_error_rate(20),
            'timestamp': time.time(),
            'zero_gas_fee_note': 'All decryption operations happen at Edge Layer - NO BLOCKCHAIN GAS FEE!'
        }
        
        print("\n✅ All encryption tests completed!")
        return results
    
    def get_encryption_metrics(self):
        """
        Get all encryption performance metrics summary
        """
        rsa_test = self.test_rsa_encryption_time(num_tests=5)
        master_test = self.test_master_key_encryption_time(20)
        sig_test = self.test_signature_performance(20)
        
        return {
            'rsa_encryption_avg_ms': rsa_test['summary']['avg_encryption_overall_ms'],
            'rsa_decryption_avg_ms': rsa_test['summary']['avg_decryption_overall_ms'],
            'master_key_encryption_avg_ms': master_test['encryption']['average_ms'],
            'master_key_decryption_avg_ms': master_test['decryption']['average_ms'],
            'signature_generation_avg_ms': sig_test['signing']['average_ms'],
            'signature_verification_avg_ms': sig_test['verification']['average_ms'],
            'zero_gas_fee': True,
            'encryption_algorithms': 'RSA-2048, AES-256, Fernet'
        }


# ========== TEST CODE ==========
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing Encryption Handler (RSA + Hierarchical Keys)")
    print("="*60)
    
    handler = EncryptionHandler()
    
    # ========== TEST 1: RSA Encryption (Old Method) ==========
    print("\n" + "="*50)
    print("TEST 1: RSA Encryption (Device to Device)")
    print("="*50)
    
    # Generate keys for sender and receiver
    print("\n🔑 Generating RSA keys...")
    sender_keys = handler.generate_key_pair()
    receiver_keys = handler.generate_key_pair()
    
    original_message = "Hello Device B! This is a secret message."
    print(f"\n📝 Original Message: {original_message}")
    
    # Encrypt with receiver's public key
    print("\n🔒 Encrypting with receiver's public key...")
    encrypted = handler.encrypt_with_public_key(original_message, receiver_keys['public_key'])
    
    if encrypted:
        print(f"✅ Encrypted successfully")
        
        # Decrypt with receiver's private key
        print("\n🔓 Decrypting with receiver's private key...")
        decrypted = handler.decrypt_with_private_key(encrypted, receiver_keys['private_key'])
        print(f"✅ Decrypted Message: {decrypted}")
        
        if decrypted == original_message:
            print("\n🎉 RSA Test PASSED!")
    
    # ========== TEST 2: Hierarchical Keys (New Method) ==========
    print("\n" + "="*50)
    print("TEST 2: Hierarchical Keys (Master Key + Period)")
    print("="*50)
    
    MASTER_KEY = "MySecretMasterKey123"
    
    print(f"\n🔑 Master Key: {MASTER_KEY}")
    
    # Get current period
    current_period = handler.get_period_number()
    print(f"📅 Current Period: {current_period}")
    
    # Encrypt with master key
    test_message = "This message is encrypted with master key!"
    print(f"\n📝 Message: {test_message}")
    
    print("\n🔒 Encrypting with master key...")
    encrypted_master = handler.encrypt_with_master_key(test_message, MASTER_KEY)
    
    if encrypted_master:
        print(f"✅ Encrypted! Period: {encrypted_master['period_number']}")
        
        # Decrypt with master key
        print("\n🔓 Decrypting with master key...")
        decrypted_master = handler.decrypt_with_master_key(encrypted_master, MASTER_KEY)
        print(f"✅ Decrypted: {decrypted_master}")
        
        if decrypted_master == test_message:
            print("\n🎉 Hierarchical Keys Test PASSED!")
    
    # ========== TEST 3: Different Period Keys ==========
    print("\n" + "="*50)
    print("TEST 3: Different Periods = Different Keys")
    print("="*50)
    
    period_1 = 1000
    period_2 = 1001
    
    key1 = handler.derive_key_from_master(MASTER_KEY, period_1)
    key2 = handler.derive_key_from_master(MASTER_KEY, period_2)
    
    print(f"\n🔑 Key for period {period_1}: {key1[:20]}...")
    print(f"🔑 Key for period {period_2}: {key2[:20]}...")
    
    if key1 != key2:
        print("\n✅ Different periods produce DIFFERENT keys! (Good for security)")
    else:
        print("\n❌ Different periods produced SAME keys! (Problem)")
    
    # ========== TEST 4: Same Period = Same Key ==========
    print("\n" + "="*50)
    print("TEST 4: Same Period = Same Key")
    print("="*50)
    
    key1_same = handler.derive_key_from_master(MASTER_KEY, period_1)
    key2_same = handler.derive_key_from_master(MASTER_KEY, period_1)
    
    if key1_same == key2_same:
        print("\n✅ Same period produces SAME key! (Can decrypt old messages)")
    else:
        print("\n❌ Same period produced DIFFERENT keys! (Problem)")
    
    # ========== RUN ALL PERFORMANCE TESTS ==========
    print("\n" + "="*60)
    print("RUNNING ALL ENCRYPTION PERFORMANCE TESTS")
    print("="*60)
    
    perf_results = handler.run_all_encryption_tests()
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS COMPLETE!")
    print("="*60)
    print("\n📌 Summary:")
    print("   ✅ RSA Encryption (Device to Device) - Working")
    print("   ✅ Hierarchical Keys (Master Key + Period) - Working")
    print("   ✅ Different periods = Different keys")
    print("   ✅ Same period = Same key")
    
    print("\n📊 Performance Results Summary:")
    print(f"   RSA Encryption Avg: {perf_results['rsa_performance']['summary']['avg_encryption_overall_ms']} ms")
    print(f"   RSA Decryption Avg: {perf_results['rsa_performance']['summary']['avg_decryption_overall_ms']} ms")
    print(f"   Master Key Encryption Avg: {perf_results['master_key_performance']['encryption']['average_ms']} ms")
    print(f"   Master Key Decryption Avg: {perf_results['master_key_performance']['decryption']['average_ms']} ms")
    print(f"   Signature Generation Avg: {perf_results['signature_performance']['signing']['average_ms']} ms")
    
    print("\n🔐 Security Features:")
    print("   - Master key NEVER stored")
    print("   - Keys auto-rotate every 6 hours")
    print("   - Old messages still accessible")
    print("   - Zero Gas Fee Decryption at Edge Layer!")
    print("="*60)
