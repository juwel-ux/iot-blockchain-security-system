# network_layer/backup.py
import json
import os
import shutil
import requests
import hashlib
from datetime import datetime
import threading
import time

class BackupManager:
    """Complete backup system for Network Layer - 3 Layer Backup"""
    
    def __init__(self, backup_dir="network_backups"):
        self.backup_dir = backup_dir
        self.backup_schedule_minutes = 30
        self.retention_days = 7
        self.is_running = False
        self.backup_thread = None
        self.peer_backup_urls = []  # Distributed backup locations
        
        # Create backup directory if not exists
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
    
    def add_peer_backup_location(self, peer_url):
        """Add peer for distributed backup (Layer 2)"""
        if peer_url not in self.peer_backup_urls:
            self.peer_backup_urls.append(peer_url)
            print(f"📀 Distributed backup location added: {peer_url}")
    
    def create_local_backup(self, registered_devices, blockchain_chain=None):
        """Layer 1: Local Backup (Edge Level)"""
        timestamp = datetime.now()
        backup_id = timestamp.strftime("%Y%m%d_%H%M%S")
        
        backup_data = {
            'backup_id': backup_id,
            'timestamp': timestamp.isoformat(),
            'version': '1.0',
            'type': 'local',
            'total_devices': len(registered_devices),
            'devices': registered_devices,
            'blockchain': blockchain_chain if blockchain_chain else []
        }
        
        # Save to JSON file
        backup_file = os.path.join(self.backup_dir, f"local_backup_{backup_id}.json")
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        # Create metadata file
        metadata = {
            'backup_id': backup_id,
            'created_at': timestamp.isoformat(),
            'file_size': os.path.getsize(backup_file),
            'device_count': len(registered_devices),
            'type': 'local'
        }
        
        metadata_file = os.path.join(self.backup_dir, f"metadata_{backup_id}.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n💾 LAYER 1 - LOCAL BACKUP: {backup_file}")
        print(f"   Devices: {len(registered_devices)}")
        print(f"   Size: {os.path.getsize(backup_file)} bytes")
        
        return backup_id
    
    def create_distributed_backup(self, registered_devices):
        """Layer 2: Distributed Backup (Network Level)"""
        if not self.peer_backup_urls:
            print("⚠️ No peer backup locations configured for distributed backup")
            return 0
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'type': 'distributed',
            'total_devices': len(registered_devices),
            'devices': registered_devices
        }
        
        success_count = 0
        for peer in self.peer_backup_urls:
            try:
                response = requests.post(
                    f"{peer}/api/network/backup/sync",
                    json=backup_data,
                    timeout=5
                )
                if response.status_code == 200:
                    success_count += 1
                    print(f"📀 Distributed backup sent to {peer}")
                else:
                    print(f"⚠️ Failed to send backup to {peer}: {response.status_code}")
            except Exception as e:
                print(f"❌ Failed to send backup to {peer}: {e}")
        
        print(f"📀 LAYER 2 - DISTRIBUTED BACKUP: {success_count}/{len(self.peer_backup_urls)} peers")
        return success_count
    
    def create_blockchain_anchor(self, registered_devices):
        """Layer 3: Blockchain Anchor (Hash Only)"""
        # Create hash of all devices (not the actual data)
        devices_list = list(registered_devices.keys())
        devices_hash = hashlib.sha256(
            json.dumps(devices_list, sort_keys=True).encode()
        ).hexdigest()
        
        # Create hash of all device details
        devices_detail_hash = hashlib.sha256(
            json.dumps(registered_devices, sort_keys=True).encode()
        ).hexdigest()
        
        anchor_data = {
            'timestamp': datetime.now().isoformat(),
            'type': 'blockchain_anchor',
            'devices_hash': devices_hash,
            'devices_detail_hash': devices_detail_hash,
            'device_count': len(registered_devices),
            'anchor_version': '1.0'
        }
        
        # Save anchor to file (simulating blockchain)
        anchor_file = os.path.join(self.backup_dir, f"blockchain_anchor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(anchor_file, 'w') as f:
            json.dump(anchor_data, f, indent=2)
        
        print(f"🔗 LAYER 3 - BLOCKCHAIN ANCHOR:")
        print(f"   Devices Hash: {devices_hash[:32]}...")
        print(f"   Detail Hash: {devices_detail_hash[:32]}...")
        print(f"   Anchor File: {anchor_file}")
        
        return anchor_data
    
    def create_full_backup(self, registered_devices, blockchain_chain=None):
        """Create all 3 layers of backup"""
        print("\n" + "="*60)
        print("📀 CREATING FULL BACKUP (3 LAYERS)")
        print("="*60)
        
        results = {}
        
        # Layer 1: Local Backup
        local_id = self.create_local_backup(registered_devices, blockchain_chain)
        results['local_backup'] = local_id
        
        # Layer 2: Distributed Backup
        dist_count = self.create_distributed_backup(registered_devices)
        results['distributed_peers'] = dist_count
        
        # Layer 3: Blockchain Anchor
        anchor = self.create_blockchain_anchor(registered_devices)
        results['blockchain_anchor'] = anchor
        
        print("="*60)
        print("✅ FULL BACKUP COMPLETE")
        print("="*60 + "\n")
        
        return results
    
    def create_backup(self, registered_devices, blockchain_chain=None):
        """Original method - now creates full 3-layer backup"""
        return self.create_full_backup(registered_devices, blockchain_chain)
    
    def restore_local_backup(self, backup_id):
        """Restore from local backup"""
        backup_file = os.path.join(self.backup_dir, f"local_backup_{backup_id}.json")
        
        if not os.path.exists(backup_file):
            # Try old format
            backup_file = os.path.join(self.backup_dir, f"backup_{backup_id}.json")
        
        if not os.path.exists(backup_file):
            print(f"❌ Backup {backup_id} not found")
            return None
        
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        print(f"\n🔄 RESTORING LOCAL BACKUP: {backup_id}")
        print(f"   Devices: {len(backup_data.get('devices', {}))}")
        print(f"   Backup time: {backup_data.get('timestamp', 'N/A')}")
        
        return backup_data.get('devices', {})
    
    def restore_from_distributed(self, peer_url):
        """Restore backup from distributed peer"""
        try:
            response = requests.get(f"{peer_url}/api/network/backup/latest", timeout=10)
            if response.status_code == 200:
                backup_data = response.json()
                print(f"🔄 Restored from distributed peer: {peer_url}")
                print(f"   Devices: {len(backup_data.get('devices', {}))}")
                return backup_data.get('devices', {})
        except Exception as e:
            print(f"❌ Failed to restore from {peer_url}: {e}")
        
        return None
    
    def verify_blockchain_anchor(self, registered_devices):
        """Verify blockchain anchor matches current devices"""
        current_hash = hashlib.sha256(
            json.dumps(list(registered_devices.keys()), sort_keys=True).encode()
        ).hexdigest()
        
        # Find latest anchor
        anchors = []
        for file in os.listdir(self.backup_dir):
            if file.startswith("blockchain_anchor_") and file.endswith(".json"):
                file_path = os.path.join(self.backup_dir, file)
                with open(file_path, 'r') as f:
                    anchor_data = json.load(f)
                anchors.append(anchor_data)
        
        if not anchors:
            print("⚠️ No blockchain anchors found")
            return False, "No anchors found"
        
        # Get latest anchor
        latest_anchor = max(anchors, key=lambda x: x.get('timestamp', ''))
        stored_hash = latest_anchor.get('devices_hash', '')
        
        if current_hash == stored_hash:
            print("✅ Blockchain anchor verification PASSED")
            return True, "Anchor verified"
        else:
            print("❌ Blockchain anchor verification FAILED")
            print(f"   Current hash: {current_hash[:32]}...")
            print(f"   Stored hash: {stored_hash[:32]}...")
            return False, "Hash mismatch"
    
    def restore_backup(self, backup_id):
        """Restore from a specific backup (backward compatible)"""
        return self.restore_local_backup(backup_id)
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.startswith("local_backup_") and file.endswith(".json"):
                backup_id = file.replace("local_backup_", "").replace(".json", "")
                file_path = os.path.join(self.backup_dir, file)
                
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                backups.append({
                    'backup_id': backup_id,
                    'timestamp': data.get('timestamp', 'N/A'),
                    'device_count': data.get('total_devices', 0),
                    'file_size': os.path.getsize(file_path),
                    'type': 'local'
                })
            elif file.startswith("backup_") and file.endswith(".json"):
                backup_id = file.replace("backup_", "").replace(".json", "")
                file_path = os.path.join(self.backup_dir, file)
                
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                backups.append({
                    'backup_id': backup_id,
                    'timestamp': data.get('timestamp', 'N/A'),
                    'device_count': data.get('total_devices', 0),
                    'file_size': os.path.getsize(file_path),
                    'type': 'legacy'
                })
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
    
    def list_blockchain_anchors(self):
        """List all blockchain anchors"""
        anchors = []
        for file in os.listdir(self.backup_dir):
            if file.startswith("blockchain_anchor_") and file.endswith(".json"):
                file_path = os.path.join(self.backup_dir, file)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                anchors.append({
                    'file': file,
                    'timestamp': data.get('timestamp', 'N/A'),
                    'device_count': data.get('device_count', 0),
                    'devices_hash': data.get('devices_hash', 'N/A')[:16] + "..."
                })
        
        return sorted(anchors, key=lambda x: x['timestamp'], reverse=True)
    
    def clean_old_backups(self):
        """Remove backups older than retention period"""
        current_time = datetime.now()
        
        for file in os.listdir(self.backup_dir):
            if file.endswith(".json"):
                file_path = os.path.join(self.backup_dir, file)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                age_days = (current_time - file_time).days
                
                if age_days > self.retention_days:
                    os.remove(file_path)
                    print(f"🗑️ Removed old backup: {file}")
    
    def start_auto_backup(self, get_devices_callback, interval_minutes=None):
        """Start automatic periodic backups"""
        if interval_minutes:
            self.backup_schedule_minutes = interval_minutes
        
        if self.is_running:
            print("Auto backup already running")
            return
        
        self.is_running = True
        
        def backup_worker():
            while self.is_running:
                time.sleep(self.backup_schedule_minutes * 60)
                try:
                    devices = get_devices_callback()
                    self.create_full_backup(devices)
                except Exception as e:
                    print(f"❌ Auto backup failed: {e}")
        
        self.backup_thread = threading.Thread(target=backup_worker, daemon=True)
        self.backup_thread.start()
        print(f"✅ Auto backup started (every {self.backup_schedule_minutes} minutes)")
    
    def stop_auto_backup(self):
        """Stop automatic backups"""
        self.is_running = False
        print("🛑 Auto backup stopped")
    
    def export_to_json(self, registered_devices, filename=None):
        """Export devices to JSON file"""
        if not filename:
            filename = f"export_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_devices': len(registered_devices),
            'devices': registered_devices
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📤 Exported {len(registered_devices)} devices to {filename}")
        return filename
    
    def import_from_json(self, filename):
        """Import devices from JSON file"""
        if not os.path.exists(filename):
            print(f"❌ File {filename} not found")
            return None
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        print(f"📥 Imported {len(data['devices'])} devices from {filename}")
        return data['devices']
    
    def get_backup_statistics(self):
        """Get backup statistics"""
        backups = self.list_backups()
        anchors = self.list_blockchain_anchors()
        
        return {
            'total_backups': len(backups),
            'total_anchors': len(anchors),
            'latest_backup': backups[0] if backups else None,
            'latest_anchor': anchors[0] if anchors else None,
            'backup_directory': self.backup_dir,
            'retention_days': self.retention_days
        }