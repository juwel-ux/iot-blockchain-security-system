import json
import time
from datetime import datetime

# network_layer/verification.py - blockchain verification 
# network_layer/verification.py - blockchain verification যোগ করুন

class VerificationEngine:
    def __init__(self):
        self.verified_devices = {}
        self.failed_attempts = {}
        self.max_failed_attempts = 3
        self.blockchain_verified = {}
    
    def verify_with_blockchain(self, virtual_id, signature, public_key):
        """Verify device with blockchain (simulated for now)"""
        try:
            # Check if device exists in blockchain
            # This will be replaced with actual smart contract call
            import hashlib
            
            # Simulate blockchain verification
            verification_hash = hashlib.sha256(
                f"{virtual_id}{signature[:20]}".encode()
            ).hexdigest()
            
            self.blockchain_verified[virtual_id] = {
                'verified': True,
                'timestamp': datetime.now().isoformat(),
                'verification_hash': verification_hash
            }
            
            print(f"🔗 Blockchain verification passed for {virtual_id}")
            return True, "Blockchain verification passed"
            
        except Exception as e:
            print(f"❌ Blockchain verification failed: {e}")
            return False, f"Blockchain verification failed: {e}"
    
    def verify_complete(self, packet, registered_devices):
        """Complete verification including blockchain"""
        
        # Previous verifications...
        verification_log = []
        
        # ... (format, timestamp, signature, uniqueness, metadata verification)
        
        # NEW: Blockchain verification
        print("\n🔗 Step 6: Blockchain verification...")
        valid, msg = self.verify_with_blockchain(
            packet.get('virtual_id'),
            packet.get('signature'),
            packet.get('public_key')
        )
        verification_log.append(f"Blockchain: {msg}")
        if not valid:
            print(f"   ❌ {msg}")
            return False, verification_log, msg
        print(f"   ✅ {msg}")
        
        return True, verification_log, "All verifications passed"