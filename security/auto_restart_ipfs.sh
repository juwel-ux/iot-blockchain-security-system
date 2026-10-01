#!/bin/bash
# auto_restart_ipfs.sh - Keep IPFS daemon running

while true; do
    # Check if IPFS daemon is running
    if ! pgrep -f "ipfs daemon" > /dev/null; then
        echo "[$(date)] IPFS daemon stopped! Restarting..."
        cd ~/Desktop
        ipfs daemon > /tmp/ipfs.log 2>&1 &
        sleep 5
        
        # Send notification
        echo "🚨 IPFS Daemon restarted at $(date)" >> ~/Desktop/iot_blockchain_project/security/ipfs_restart.log
    fi
    sleep 30
done
