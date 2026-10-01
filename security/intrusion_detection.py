#!/usr/bin/env python3
# intrusion_detection.py - Real-time Intrusion Detection

import psutil
import socket
import subprocess
import time
import logging
import json
import os
from datetime import datetime
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/emdad/Desktop/iot_blockchain_project/security/ids.log'),
        logging.StreamHandler()
    ]
)

class IntrusionDetectionSystem:
    def __init__(self):
        self.suspicious_processes = [
            'nc', 'netcat', 'nmap', 'hydra', 'john', 'aircrack',
            'metasploit', 'msfconsole', 'sqlmap', 'burpsuite',
            'wireshark', 'tcpdump', 'ettercap', 'bettercap'
        ]
        
        self.suspicious_ports = [22, 23, 3389, 5900, 4444, 5555, 6666, 7777, 8888, 9999]
        self.failed_logins = defaultdict(list)
        self.alert_count = 0
        
    def detect_suspicious_processes(self):
        """Detect known hacking tools"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
                
                for suspicious in self.suspicious_processes:
                    if suspicious in proc_name or suspicious in cmdline:
                        self.trigger_alert(
                            "SUSPICIOUS_PROCESS",
                            f"Process '{proc_name}' with PID {proc.info['pid']}",
                            proc.info['cmdline']
                        )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def detect_unauthorized_connections(self):
        """Detect unusual network connections"""
        try:
            connections = psutil.net_connections()
            for conn in connections:
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    remote_port = conn.raddr.port
                    if remote_port in self.suspicious_ports:
                        self.trigger_alert(
                            "SUSPICIOUS_CONNECTION",
                            f"Connection to port {remote_port} from {conn.raddr.ip}",
                            f"PID: {conn.pid}"
                        )
        except Exception as e:
            logging.error(f"Connection detection error: {e}")
    
    def detect_failed_login_attempts(self, username):
        """Track failed login attempts"""
        now = time.time()
        self.failed_logins[username].append(now)
        
        # Remove old attempts (> 5 minutes)
        self.failed_logins[username] = [t for t in self.failed_logins[username] if now - t < 300]
        
        if len(self.failed_logins[username]) >= 5:
            self.trigger_alert(
                "BRUTE_FORCE_ATTEMPT",
                f"5+ failed login attempts for user '{username}' in 5 minutes",
                f"Total attempts: {len(self.failed_logins[username])}"
            )
            return False
        return True
    
    def trigger_alert(self, alert_type, message, details):
        """Trigger security alert"""
        self.alert_count += 1
        
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'details': details,
            'alert_number': self.alert_count
        }
        
        # Log to file
        logging.error(f"🚨 ALERT: {alert_type} - {message}")
        
        # Save to JSON log
        log_file = '/home/emdad/Desktop/iot_blockchain_project/security/alerts.json'
        try:
            with open(log_file, 'r') as f:
                alerts = json.load(f)
        except:
            alerts = []
        
        alerts.append(alert_data)
        
        with open(log_file, 'w') as f:
            json.dump(alerts[-100:], f, indent=2)  # Keep last 100 alerts
        
        # Optional: Send to your phone (if you have webhook)
        self.send_webhook_alert(alert_data)
    
    def send_webhook_alert(self, alert_data):
        """Send alert to external service (Discord/Telegram/Webhook)"""
        # Example for Discord webhook (if you have one)
        # webhook_url = "YOUR_DISCORD_WEBHOOK_URL"
        # requests.post(webhook_url, json={"content": f"🚨 {alert_data['type']}: {alert_data['message']}"})
        
        # For now, just print
        print(f"\n{'='*50}")
        print(f"🚨 SECURITY ALERT!")
        print(f"   Type: {alert_data['type']}")
        print(f"   Message: {alert_data['message']}")
        print(f"   Time: {alert_data['timestamp']}")
        print(f"{'='*50}\n")
    
    def scan_system_files(self):
        """Scan critical system files for changes"""
        critical_files = [
            '/etc/passwd',
            '/etc/shadow',
            '/etc/sudoers',
            '/home/emdad/.bashrc',
            '/home/emdad/.ssh/authorized_keys'
        ]
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                try:
                    stat = os.stat(file_path)
                    current_mtime = stat.st_mtime
                    
                    # Check against previous mtime
                    cache_file = f'/tmp/ids_{file_path.replace("/", "_")}.cache'
                    if os.path.exists(cache_file):
                        with open(cache_file, 'r') as f:
                            old_mtime = float(f.read())
                        if current_mtime != old_mtime:
                            self.trigger_alert(
                                "FILE_CHANGED",
                                f"Critical file changed: {file_path}",
                                f"Old: {old_mtime}, New: {current_mtime}"
                            )
                    
                    with open(cache_file, 'w') as f:
                        f.write(str(current_mtime))
                except:
                    pass
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        logging.info("🛡️ Intrusion Detection System Started")
        print("\n" + "="*50)
        print("🛡️ INTRUSION DETECTION SYSTEM ACTIVE")
        print("   Monitoring for:")
        print("   - Suspicious processes")
        print("   - Unauthorized connections")
        print("   - Failed login attempts")
        print("   - Critical file changes")
        print("="*50 + "\n")
        
        while True:
            try:
                self.detect_suspicious_processes()
                self.detect_unauthorized_connections()
                self.scan_system_files()
                time.sleep(5)  # Scan every 5 seconds
            except KeyboardInterrupt:
                print("\n🛑 IDS Stopped")
                break
            except Exception as e:
                logging.error(f"IDS Error: {e}")
                time.sleep(10)


if __name__ == "__main__":
    ids = IntrusionDetectionSystem()
    ids.start_monitoring()
