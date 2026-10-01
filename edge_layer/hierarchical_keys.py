# edge_layer/hierarchical_keys.py
"""
Hierarchical Key Management System
Master Key + Period Number → Unique Keys for each time period
Keys auto-rotate every 6 hours
Old messages remain accessible
"""

import time
import base64
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from datetime import datetime, timedelta


class HierarchicalKeyManager:
    """
    Manages hierarchical keys derived from master key
    Master key NEVER stored - only hash kept for verification
    """
    
    def __init__(self):
        self.master_key_hash = None
        self.cached_keys = {}  # Cache recently used keys (period -> key)
        self.cache_timeout = 3600  # Clear cache after 1 hour
        
    # ========== PERIOD CALCULATION ==========
    
    def get_period_seconds(self):
        """Get period length in seconds (6 hours = 21600 seconds)"""
        return 6 * 3600  # 21600
    
    def get_period_number(self, timestamp=None):
        """
        Get 6-hour period number from timestamp
        Period 0: 00:00-06:00, Period 1: 06:00-12:00, etc.
        Never stops - always increases with time
        """
        if timestamp is None:
            timestamp = time.time()
        
        period_seconds = self.get_period_seconds()
        period_number = int(timestamp // period_seconds)
        
        return period_number
    
    def get_period_start_time(self, period_number):
        """Get start timestamp of a period"""
        period_seconds = self.get_period_seconds()
        return period_number * period_seconds
    
    def get_period_end_time(self, period_number):
        """Get end timestamp of a period"""
        period_seconds = self.get_period_seconds()
        return (period_number + 1) * period_seconds
    
    def get_current_period(self):
        """Get current period number"""
        return self.get_period_number()
    
    def get_next_period(self, period_number=None):
        """Get next period number"""
        if period_number is None:
            period_number = self.get_current_period()
        return period_number + 1
    
    def get_previous_period(self, period_number=None):
        """Get previous period number"""
        if period_number is None:
            period_number = self.get_current_period()
        return period_number - 1 if period_number > 0 else 0
    
    def get_period_range(self, start_timestamp, end_timestamp):
        """Get all period numbers between two timestamps"""
        start_period = self.get_period_number(start_timestamp)
        end_period = self.get_period_number(end_timestamp)
        
        return list(range(start_period, end_period + 1))
    
    def get_periods_in_last_days(self, days=30):
        """Get all period numbers in last N days"""
        now = time.time()
        start = now - (days * 24 * 3600)
        return self.get_period_range(start, now)
    
    # ========== KEY DERIVATION ==========
    
    def derive_key_from_master(self, master_key, period_number):
        """
        Derive unique key from master key + period number
        Same master key + same period = same derived key
        Different period = different derived key
        """
        # Create unique salt for each period
        salt = f"iot_blockchain_hierarchical_period_{period_number}".encode('utf-8')
        
        # PBKDF2 with 100,000 iterations (slow for brute force)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256-bit key
            salt=salt,
            iterations=100000,
        )
        
        derived_key = kdf.derive(master_key.encode('utf-8'))
        
        # Return as base64 for Fernet compatibility
        return base64.urlsafe_b64encode(derived_key)
    
    def get_key_for_period(self, master_key, period_number, use_cache=True):
        """
        Get derived key for a period (with optional caching)
        """
        # Check cache first
        if use_cache and period_number in self.cached_keys:
            cache_entry = self.cached_keys[period_number]
            if time.time() - cache_entry['timestamp'] < self.cache_timeout:
                return cache_entry['key']
        
        # Derive new key
        key = self.derive_key_from_master(master_key, period_number)
        
        # Cache it
        if use_cache:
            self.cached_keys[period_number] = {
                'key': key,
                'timestamp': time.time()
            }
            # Clean old cache entries
            self._clean_cache()
        
        return key
    
    def get_key_for_current_period(self, master_key):
        """Get key for current period"""
        period = self.get_current_period()
        return self.get_key_for_period(master_key, period)
    
    def get_key_for_timestamp(self, master_key, timestamp):
        """Get key for a specific timestamp"""
        period = self.get_period_number(timestamp)
        return self.get_key_for_period(master_key, period)
    
    def _clean_cache(self):
        """Remove old entries from cache"""
        current_time = time.time()
        to_remove = []
        
        for period, entry in self.cached_keys.items():
            if current_time - entry['timestamp'] > self.cache_timeout:
                to_remove.append(period)
        
        for period in to_remove:
            del self.cached_keys[period]
    
    def clear_cache(self):
        """Clear all cached keys"""
        self.cached_keys.clear()
    
    # ========== ENCRYPTION/DECRYPTION ==========
    
    def encrypt_with_master_key(self, data, master_key, period_number=None):
        """
        Encrypt data using master key derived key
        If period_number not provided, uses current period
        """
        if period_number is None:
            period_number = self.get_current_period()
        
        derived_key = self.get_key_for_period(master_key, period_number)
        cipher = Fernet(derived_key)
        
        # Encrypt data
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        encrypted_data = cipher.encrypt(data_bytes)
        
        return {
            'encrypted_data': base64.b64encode(encrypted_data).decode('utf-8'),
            'period_number': period_number,
            'timestamp': time.time(),
            'encryption_type': 'hierarchical_master_key'
        }
    
    def decrypt_with_master_key(self, encrypted_data, master_key):
        """
        Decrypt data using master key derived key
        Automatically uses period_number from encrypted data
        """
        period_number = encrypted_data.get('period_number')
        
        if period_number is None:
            # Try to detect period from timestamp
            timestamp = encrypted_data.get('timestamp', time.time())
            period_number = self.get_period_number(timestamp)
        
        derived_key = self.get_key_for_period(master_key, period_number)
        cipher = Fernet(derived_key)
        
        encrypted_bytes = base64.b64decode(encrypted_data['encrypted_data'])
        decrypted_data = cipher.decrypt(encrypted_bytes)
        
        return decrypted_data.decode('utf-8')
    
    # ========== MASTER KEY VERIFICATION ==========
    
    def hash_master_key(self, master_key):
        """Create secure hash of master key (never store the key itself)"""
        # Use SHA-256 with salt
        salt = b'iot_blockchain_master_key_salt'
        return hashlib.pbkdf2_hmac(
            'sha256',
            master_key.encode('utf-8'),
            salt,
            100000
        ).hex()
    
    def set_master_key_hash(self, master_key):
        """Store only the hash of master key"""
        self.master_key_hash = self.hash_master_key(master_key)
        return self.master_key_hash
    
    def verify_master_key(self, master_key):
        """Verify if provided master key matches stored hash"""
        if self.master_key_hash is None:
            return True
        return self.hash_master_key(master_key) == self.master_key_hash
    
    # ========== UTILITY FUNCTIONS ==========
    
    def is_same_period(self, timestamp1, timestamp2):
        """Check if two timestamps are in the same period"""
        period1 = self.get_period_number(timestamp1)
        period2 = self.get_period_number(timestamp2)
        return period1 == period2
    
    def get_time_until_next_period(self):
        """Get seconds until next period starts"""
        current_period = self.get_current_period()
        next_period_start = self.get_period_start_time(current_period + 1)
        return next_period_start - time.time()
    
    def get_time_until_next_period_human(self):
        """Get human readable time until next period"""
        seconds = self.get_time_until_next_period()
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def get_period_info(self, period_number=None):
        """Get detailed information about a period"""
        if period_number is None:
            period_number = self.get_current_period()
        
        start_time = self.get_period_start_time(period_number)
        end_time = self.get_period_end_time(period_number)
        
        return {
            'period_number': period_number,
            'start_time': datetime.fromtimestamp(start_time).isoformat(),
            'end_time': datetime.fromtimestamp(end_time).isoformat(),
            'duration_hours': 6,
            'is_current': period_number == self.get_current_period()
        }
    
    def get_statistics(self):
        """Get statistics about key manager"""
        return {
            'master_key_hash_set': self.master_key_hash is not None,
            'cached_keys_count': len(self.cached_keys),
            'period_seconds': self.get_period_seconds(),
            'period_hours': self.get_period_seconds() / 3600,
            'current_period': self.get_current_period(),
            'time_until_next_period': self.get_time_until_next_period_human()
        }


# ========== SINGLETON INSTANCE ==========
_hierarchical_key_manager = None

def get_hierarchical_key_manager():
    """Get singleton instance of HierarchicalKeyManager"""
    global _hierarchical_key_manager
    if _hierarchical_key_manager is None:
        _hierarchical_key_manager = HierarchicalKeyManager()
    return _hierarchical_key_manager


# ========== TEST CODE ==========
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🔐 HIERARCHICAL KEY MANAGER TEST")
    print("="*70)
    
    km = HierarchicalKeyManager()
    MASTER_KEY = "MySecretMasterKey123"
    
    # ========== TEST 1: Period Calculation ==========
    print("\n" + "="*50)
    print("TEST 1: Period Calculation")
    print("="*50)
    
    current_period = km.get_current_period()
    print(f"\n📅 Current Period: {current_period}")
    print(f"⏰ Time until next period: {km.get_time_until_next_period_human()}")
    
    period_info = km.get_period_info(current_period)
    print(f"📆 Period {current_period}: {period_info['start_time']} to {period_info['end_time']}")
    
    # ========== TEST 2: Key Derivation ==========
    print("\n" + "="*50)
    print("TEST 2: Key Derivation")
    print("="*50)
    
    key1 = km.derive_key_from_master(MASTER_KEY, current_period)
    key2 = km.derive_key_from_master(MASTER_KEY, current_period)
    
    print(f"\n🔑 Key (first 30 chars): {key1[:30]}...")
    print(f"🔑 Same key derived again: {key2[:30]}...")
    
    if key1 == key2:
        print("\n✅ Same period = SAME key!")
    else:
        print("\n❌ Same period = DIFFERENT keys!")
    
    # Different period
    next_period = current_period + 1
    key_next = km.derive_key_from_master(MASTER_KEY, next_period)
    print(f"\n🔑 Next period key: {key_next[:30]}...")
    
    if key1 != key_next:
        print("\n✅ Different period = DIFFERENT keys!")
    else:
        print("\n❌ Different period = SAME keys!")
    
    # ========== TEST 3: Encryption/Decryption ==========
    print("\n" + "="*50)
    print("TEST 3: Encryption/Decryption")
    print("="*50)
    
    test_message = "This is a secret message that will be encrypted with master key!"
    print(f"\n📝 Original: {test_message}")
    
    # Encrypt
    encrypted = km.encrypt_with_master_key(test_message, MASTER_KEY)
    print(f"\n🔒 Encrypted: {encrypted['encrypted_data'][:50]}...")
    print(f"   Period: {encrypted['period_number']}")
    
    # Decrypt
    decrypted = km.decrypt_with_master_key(encrypted, MASTER_KEY)
    print(f"\n🔓 Decrypted: {decrypted}")
    
    if decrypted == test_message:
        print("\n✅ Encryption/Decryption WORKING!")
    else:
        print("\n❌ Encryption/Decryption FAILED!")
    
    # ========== TEST 4: Cross-Period Decryption ==========
    print("\n" + "="*50)
    print("TEST 4: Cross-Period Decryption")
    print("="*50)
    
    # Encrypt with old period (simulate old message)
    old_period = current_period - 5 if current_period > 5 else 0
    encrypted_old = km.encrypt_with_master_key(test_message, MASTER_KEY, old_period)
    print(f"\n📦 Message encrypted in period {old_period}")
    
    # Decrypt now (different period)
    decrypted_old = km.decrypt_with_master_key(encrypted_old, MASTER_KEY)
    print(f"🔓 Decrypted now (period {current_period}): {decrypted_old}")
    
    if decrypted_old == test_message:
        print("\n✅ Old messages can be decrypted in current period!")
    else:
        print("\n❌ Cannot decrypt old messages!")
    
    # ========== TEST 5: Master Key Hash ==========
    print("\n" + "="*50)
    print("TEST 5: Master Key Hash (No Key Storage)")
    print("="*50)
    
    km.set_master_key_hash(MASTER_KEY)
    print(f"\n🔐 Master Key Hash: {km.master_key_hash[:32]}...")
    
    is_valid = km.verify_master_key(MASTER_KEY)
    print(f"✅ Correct key verification: {is_valid}")
    
    is_valid = km.verify_master_key("WrongKey123")
    print(f"❌ Wrong key verification: {is_valid}")
    
    # ========== TEST 6: Statistics ==========
    print("\n" + "="*50)
    print("TEST 6: Statistics")
    print("="*50)
    
    stats = km.get_statistics()
    print(f"\n📊 Statistics:")
    print(f"   Period length: {stats['period_hours']} hours")
    print(f"   Current period: {stats['current_period']}")
    print(f"   Time until next period: {stats['time_until_next_period']}")
    print(f"   Cached keys: {stats['cached_keys_count']}")
    print(f"   Master key hash set: {stats['master_key_hash_set']}")
    
    # ========== TEST 7: Period Range ==========
    print("\n" + "="*50)
    print("TEST 7: Period Range")
    print("="*50)
    
    now = time.time()
    one_day_ago = now - (24 * 3600)
    periods = km.get_period_range(one_day_ago, now)
    print(f"\n📅 Periods in last 24 hours: {periods}")
    print(f"   Total periods: {len(periods)}")
    
    # ========== FINAL SUMMARY ==========
    print("\n" + "="*70)
    print("📊 HIERARCHICAL KEY MANAGER SUMMARY")
    print("="*70)
    print("""
    ✅ FEATURES:
       - Master key NEVER stored (only hash)
       - Keys auto-rotate every 6 hours
       - Old messages remain accessible
       - Period numbers never stop (always increasing)
       - Cache for performance
       - PBKDF2 with 100,000 iterations
    
    🔐 SECURITY:
       - Different periods = different keys
       - Same period = same key (for decryption)
       - Master key required for decryption
       - No key stored in plain text
    
    📦 USAGE:
       from edge_layer.hierarchical_keys import get_hierarchical_key_manager
       km = get_hierarchical_key_manager()
       encrypted = km.encrypt_with_master_key(message, master_key)
       decrypted = km.decrypt_with_master_key(encrypted, master_key)
    """)
    
    print("="*70)
    print("🎉 Hierarchical Key Manager READY!")
    print("="*70)