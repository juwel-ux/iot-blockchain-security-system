# security/rate_limiter.py
from collections import defaultdict
import time
import json
import os
from datetime import datetime

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.request_counts = defaultdict(list)
        self.blocked_devices = {}
        self.log_file = '/home/emdad/Desktop/iot_blockchain_project/security/rate_limit.log'
    
    def check_rate_limit(self, device_id, action="decrypt", max_attempts=5, time_window=300):
        """
        Check if device exceeds rate limit
        - max_attempts: maximum attempts in time_window seconds
        - time_window: time window in seconds
        """
        now = time.time()
        
        # Check if device is permanently blocked
        if device_id in self.blocked_devices:
            block_time = self.blocked_devices[device_id]
            if now - block_time < 3600:  # Blocked for 1 hour
                self._log(f"BLOCKED: {device_id} - Still blocked")
                return False
            else:
                del self.blocked_devices[device_id]
        
        # Clean old attempts
        self.failed_attempts[device_id] = [
            t for t in self.failed_attempts[device_id] if now - t < time_window
        ]
        
        # Check limit
        if len(self.failed_attempts[device_id]) >= max_attempts:
            self.blocked_devices[device_id] = now
            self._log(f"RATE_LIMIT_EXCEEDED: {device_id} - Blocked for 1 hour")
            return False
        
        return True
    
    def record_failed_attempt(self, device_id, action, details=""):
        """Record a failed attempt"""
        now = time.time()
        self.failed_attempts[device_id].append(now)
        self._log(f"FAILED_ATTEMPT: {device_id} - {action} - {details}")
        
        # Trigger alert if many failures
        if len(self.failed_attempts[device_id]) >= 3:
            self._trigger_alert(device_id, action)
    
    def record_successful_attempt(self, device_id, action):
        """Record a successful attempt (resets failure count)"""
        self.failed_attempts[device_id] = []
        self._log(f"SUCCESS: {device_id} - {action}")
    
    def _log(self, message):
        """Log to file"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} - {message}\n"
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
        except:
            pass
    
    def _trigger_alert(self, device_id, action):
        """Trigger alert for suspicious activity"""
        print(f"\n🚨 ALERT: Multiple failed attempts from {device_id} for {action}")
        
        # You can add webhook notification here
        # send_webhook_alert(f"Suspicious activity from {device_id}")
    
    def get_stats(self, device_id=None):
        """Get rate limiting statistics"""
        if device_id:
            return {
                'failed_attempts': len(self.failed_attempts[device_id]),
                'is_blocked': device_id in self.blocked_devices
            }
        
        return {
            'total_failed': sum(len(v) for v in self.failed_attempts.values()),
            'blocked_devices': len(self.blocked_devices),
            'active_devices': len(self.failed_attempts)
        }


# Create singleton instance
rate_limiter = RateLimiter()
