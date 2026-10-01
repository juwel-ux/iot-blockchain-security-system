#!/usr/bin/env python3
# security_monitor.py - Main Security Monitor

import subprocess
import threading
import time
import os
import sys

def run_script(script_path, name):
    """Run a script in background"""
    try:
        process = subprocess.Popen(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        print(f"✅ {name} started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def main():
    print("\n" + "="*60)
    print("🛡️ IoT BLOCKCHAIN SECURITY MONITOR")
    print("="*60)
    print("Starting security modules...\n")
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Start all security scripts
    processes = []
    
    # 1. Auto Backup (runs every hour via cron, not continuous)
    print("📦 Auto Backup: Scheduled (every 6 hours)")
    
    # 2. Intrusion Detection
    ids_process = subprocess.Popen(
        [sys.executable, os.path.join(script_dir, 'intrusion_detection.py')],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(('Intrusion Detection', ids_process))
    
    # 3. IPFS Auto Restart
    ipfs_monitor = subprocess.Popen(
        [os.path.join(script_dir, 'auto_restart_ipfs.sh')],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(('IPFS Monitor', ipfs_monitor))
    
    print("\n" + "="*60)
    print("✅ ALL SECURITY MODULES ACTIVE")
    print("="*60)
    print("\nMonitoring:")
    print("  - Suspicious processes")
    print("  - Network connections")
    print("  - Failed login attempts")
    print("  - IPFS daemon status")
    print("  - Rate limiting active")
    print("\nPress Ctrl+C to stop all monitors\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping all security modules...")
        for name, proc in processes:
            proc.terminate()
            print(f"   Stopped {name}")
        print("✅ All modules stopped")

if __name__ == "__main__":
    main()
