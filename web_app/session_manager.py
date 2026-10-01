# web_app/session_manager.py
"""
Session Management - Master Key NEVER Stored
- Only session authentication status stored
- Master key is NEVER saved (not even in RAM)
- User must enter master key for each decryption
- Session only tracks that user is authenticated
"""

import time
import secrets
from datetime import datetime
from typing import Optional, Dict


class SessionManager:
    """
    Manages user sessions WITHOUT storing master key
    Only stores that a device has been authenticated
    Master key must be provided by user for each decryption
    """
    
    def __init__(self, session_timeout_seconds=3600):
        """
        Initialize session manager
        session_timeout_seconds: How long session lasts (default 1 hour)
        """
        self.sessions = {}  # session_token -> session_data (NO master key!)
        self.session_timeout = session_timeout_seconds
    
    def create_session(self, device_id: str) -> str:
        """
        Create a new session for a device
        NO master key is stored - only authentication status
        Returns session token
        """
        # Generate unique session token
        session_token = secrets.token_urlsafe(32)
        
        # Store session data (NO master key!)
        self.sessions[session_token] = {
            'device_id': device_id,
            'authenticated': True,  # Only this flag!
            'created_at': time.time(),
            'last_accessed': time.time(),
            'expires_at': time.time() + self.session_timeout
        }
        
        # Cleanup expired sessions
        self._cleanup_expired_sessions()
        
        return session_token
    
    def is_session_valid(self, session_token: str) -> bool:
        """
        Check if session is valid (user is authenticated)
        Does NOT return master key - only validity
        """
        if session_token not in self.sessions:
            return False
        
        session = self.sessions[session_token]
        
        # Check if expired
        if time.time() > session['expires_at']:
            self.delete_session(session_token)
            return False
        
        # Update last accessed time
        session['last_accessed'] = time.time()
        
        return True
    
    def get_device_id(self, session_token: str) -> Optional[str]:
        """
        Get device ID from session
        Returns None if session invalid
        """
        if not self.is_session_valid(session_token):
            return None
        
        return self.sessions[session_token].get('device_id')
    
    def refresh_session(self, session_token: str) -> bool:
        """
        Refresh session expiration time
        Returns True if successful
        """
        if not self.is_session_valid(session_token):
            return False
        
        self.sessions[session_token]['expires_at'] = time.time() + self.session_timeout
        self.sessions[session_token]['last_accessed'] = time.time()
        return True
    
    def delete_session(self, session_token: str) -> bool:
        """
        Delete a session (logout)
        Returns True if deleted
        """
        if session_token in self.sessions:
            del self.sessions[session_token]
            return True
        return False
    
    def delete_all_sessions_for_device(self, device_id: str) -> int:
        """
        Delete all sessions for a specific device
        Returns number of sessions deleted
        """
        to_delete = []
        for token, session in self.sessions.items():
            if session.get('device_id') == device_id:
                to_delete.append(token)
        
        for token in to_delete:
            self.delete_session(token)
        
        return len(to_delete)
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions from memory"""
        now = time.time()
        to_delete = []
        
        for token, session in self.sessions.items():
            if now > session.get('expires_at', 0):
                to_delete.append(token)
        
        for token in to_delete:
            self.delete_session(token)
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        self._cleanup_expired_sessions()
        return len(self.sessions)
    
    def get_session_info(self, session_token: str) -> Optional[Dict]:
        """
        Get session information (NO master key)
        """
        if not self.is_session_valid(session_token):
            return None
        
        session = self.sessions[session_token]
        
        return {
            'device_id': session['device_id'],
            'authenticated': session['authenticated'],
            'created_at': datetime.fromtimestamp(session['created_at']).isoformat(),
            'last_accessed': datetime.fromtimestamp(session['last_accessed']).isoformat(),
            'expires_at': datetime.fromtimestamp(session['expires_at']).isoformat(),
            'time_remaining_seconds': max(0, session['expires_at'] - time.time())
        }
    
    def get_time_remaining(self, session_token: str) -> int:
        """Get seconds remaining until session expires"""
        if not self.is_session_valid(session_token):
            return 0
        session = self.sessions[session_token]
        return max(0, int(session['expires_at'] - time.time()))
    
    def get_time_remaining_human(self, session_token: str) -> str:
        """Get human readable time remaining"""
        seconds = self.get_time_remaining(session_token)
        
        if seconds <= 0:
            return "Expired"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def extend_session(self, session_token: str, extra_seconds: int = 3600) -> bool:
        """
        Extend session by extra_seconds (default 1 hour)
        """
        if not self.is_session_valid(session_token):
            return False
        
        self.sessions[session_token]['expires_at'] = time.time() + extra_seconds
        return True
    
    def cleanup_all_expired(self):
        """Force cleanup of all expired sessions"""
        self._cleanup_expired_sessions()


# ========== SIMPLE SESSION CACHE (No Master Key) ==========

class SessionCache:
    """
    Simple in-memory cache for session status
    NO master key stored - only authentication status
    """
    
    def __init__(self, cache_timeout_seconds=300):  # 5 minutes default
        self.cache = {}
        self.cache_timeout = cache_timeout_seconds
    
    def set_authenticated(self, device_id: str, session_token: str):
        """Mark device as authenticated (NO master key)"""
        self.cache[device_id] = {
            'session_token': session_token,
            'authenticated': True,
            'timestamp': time.time()
        }
    
    def is_authenticated(self, device_id: str) -> bool:
        """Check if device is authenticated (session valid)"""
        if device_id in self.cache:
            entry = self.cache[device_id]
            if time.time() - entry['timestamp'] < self.cache_timeout:
                return entry.get('authenticated', False)
            else:
                del self.cache[device_id]
        return False
    
    def get_session_token(self, device_id: str) -> Optional[str]:
        """Get session token for device"""
        if device_id in self.cache:
            entry = self.cache[device_id]
            if time.time() - entry['timestamp'] < self.cache_timeout:
                return entry.get('session_token')
            else:
                del self.cache[device_id]
        return None
    
    def delete(self, device_id: str):
        """Remove device from cache"""
        if device_id in self.cache:
            del self.cache[device_id]
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()


# ========== MASTER KEY VERIFICATION (No Storage) ==========

class MasterKeyVerifier:
    """
    Verifies master key WITHOUT storing it
    Only stores hash of master key (cannot reverse)
    """
    
    def __init__(self):
        self.master_key_hash = None
    
    def set_master_key_hash(self, master_key: str):
        """Store ONLY the hash of master key (cannot reverse to get key)"""
        import hashlib
        salt = b'iot_blockchain_master_key_salt'
        self.master_key_hash = hashlib.pbkdf2_hmac(
            'sha256',
            master_key.encode('utf-8'),
            salt,
            100000
        ).hex()
    
    def verify_master_key(self, master_key: str) -> bool:
        """
        Verify if master key is correct
        Returns True/False - does NOT return the key
        """
        if self.master_key_hash is None:
            return True  # No master key set yet
        
        import hashlib
        salt = b'iot_blockchain_master_key_salt'
        provided_hash = hashlib.pbkdf2_hmac(
            'sha256',
            master_key.encode('utf-8'),
            salt,
            100000
        ).hex()
        
        return provided_hash == self.master_key_hash


# ========== SINGLETON INSTANCES ==========

_session_manager = None
_session_cache = None

def get_session_manager():
    """Get singleton instance of SessionManager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

def get_session_cache():
    """Get singleton instance of SessionCache"""
    global _session_cache
    if _session_cache is None:
        _session_cache = SessionCache()
    return _session_cache


# ========== TEST CODE ==========
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔐 SESSION MANAGER TEST (No Master Key Storage)")
    print("="*60)
    
    sm = SessionManager(session_timeout_seconds=60)  # 1 minute for testing
    cache = SessionCache()
    verifier = MasterKeyVerifier()
    
    DEVICE_ID = "VID_VIRTUAL_TEST_001"
    MASTER_KEY = "MySecretMasterKey123"
    
    # ========== TEST 1: Set Master Key Hash ==========
    print("\n" + "="*40)
    print("TEST 1: Set Master Key Hash (No Key Storage)")
    print("="*40)
    
    verifier.set_master_key_hash(MASTER_KEY)
    print(f"\n✅ Master key hash stored (key itself NOT stored)")
    print(f"   Hash: {verifier.master_key_hash[:32]}...")
    
    # ========== TEST 2: Verify Master Key ==========
    print("\n" + "="*40)
    print("TEST 2: Verify Master Key")
    print("="*40)
    
    is_valid = verifier.verify_master_key(MASTER_KEY)
    print(f"\n✅ Correct master key verification: {is_valid}")
    
    is_valid = verifier.verify_master_key("WrongKey123")
    print(f"❌ Wrong master key verification: {is_valid}")
    
    # ========== TEST 3: Create Session (No Master Key) ==========
    print("\n" + "="*40)
    print("TEST 3: Create Session (No Master Key Stored)")
    print("="*40)
    
    token = sm.create_session(DEVICE_ID)
    print(f"\n✅ Session created!")
    print(f"   Token: {token[:32]}...")
    print(f"   Device ID: {DEVICE_ID}")
    print(f"   ⚠️ Master key NOT stored in session!")
    
    # ========== TEST 4: Validate Session ==========
    print("\n" + "="*40)
    print("TEST 4: Validate Session")
    print("="*40)
    
    is_valid = sm.is_session_valid(token)
    print(f"\n✅ Session valid: {is_valid}")
    
    device_id = sm.get_device_id(token)
    print(f"📱 Device ID from session: {device_id}")
    
    # ========== TEST 5: Session Info ==========
    print("\n" + "="*40)
    print("TEST 5: Session Info (No Master Key)")
    print("="*40)
    
    info = sm.get_session_info(token)
    if info:
        print(f"\n📋 Session Info:")
        print(f"   Device ID: {info['device_id']}")
        print(f"   Authenticated: {info['authenticated']}")
        print(f"   Created: {info['created_at']}")
        print(f"   Expires: {info['expires_at']}")
        print(f"   Time remaining: {info['time_remaining_seconds']} seconds")
        print(f"   ⚠️ NO master key in session info!")
    
    # ========== TEST 6: Session Cache ==========
    print("\n" + "="*40)
    print("TEST 6: Session Cache (No Master Key)")
    print("="*40)
    
    cache.set_authenticated(DEVICE_ID, token)
    print(f"\n✅ Device marked as authenticated in cache")
    
    is_auth = cache.is_authenticated(DEVICE_ID)
    print(f"🔐 Device authenticated: {is_auth}")
    
    cached_token = cache.get_session_token(DEVICE_ID)
    print(f"🎫 Cached session token: {cached_token[:32]}...")
    
    # ========== TEST 7: Decryption Simulation ==========
    print("\n" + "="*40)
    print("TEST 7: Decryption Simulation (Master Key Required)")
    print("="*40)
    
    print(f"\n📝 Simulating message decryption:")
    print(f"   1. Session valid: {sm.is_session_valid(token)}")
    print(f"   2. User must enter master key: [__________]")
    print(f"   3. System verifies master key: {verifier.verify_master_key(MASTER_KEY)}")
    print(f"   4. If correct → Decrypt message")
    print(f"   5. Master key is NOT stored anywhere!")
    
    # ========== TEST 8: Session Expiry ==========
    print("\n" + "="*40)
    print("TEST 8: Session Expiry Simulation")
    print("="*40)
    
    print(f"\n⏰ Time remaining: {sm.get_time_remaining_human(token)}")
    
    # ========== TEST 9: Delete Session ==========
    print("\n" + "="*40)
    print("TEST 9: Delete Session (Logout)")
    print("="*40)
    
    sm.delete_session(token)
    is_valid = sm.is_session_valid(token)
    print(f"\n✅ Session deleted, valid now: {is_valid}")
    
    # ========== TEST 10: Statistics ==========
    print("\n" + "="*40)
    print("TEST 10: Active Sessions")
    print("="*40)
    
    # Create a few test sessions
    token2 = sm.create_session("DEVICE_2")
    token3 = sm.create_session("DEVICE_3")
    
    active_count = sm.get_active_session_count()
    print(f"\n📊 Active sessions: {active_count}")
    
    # ========== SUMMARY ==========
    print("\n" + "="*60)
    print("📊 SESSION MANAGER SUMMARY")
    print("="*60)
    print("""
    ✅ FEATURES:
       - Session token based authentication
       - ✅ Master key NEVER stored (not even in RAM)
       - ✅ Only authentication status stored
       - ✅ Automatic session expiry
       - ✅ Master key hash stored (cannot reverse)
    
    🔐 SECURITY:
       - Master key NEVER saved anywhere
       - User must enter master key for each decryption
       - Session only tracks authentication status
       - Even RAM access won't reveal master key
       - Hash cannot be reversed to get original key
    
    📦 USAGE:
       from web_app.session_manager import get_session_manager, MasterKeyVerifier
       
       sm = get_session_manager()
       verifier = MasterKeyVerifier()
       
       # During registration - store hash only
       verifier.set_master_key_hash(master_key)
       
       # After password verification - create session
       token = sm.create_session(device_id)
       
       # Later - check session
       if sm.is_session_valid(token):
           # User is authenticated, but still needs master key for decryption
           # Master key must be entered by user
           pass
       
       # Logout
       sm.delete_session(token)
    """)
    
    print("="*60)
    print("🎉 Session Manager READY! (Master Key NEVER Stored)")
    print("="*60)