# network_layer/sync.py
import json
import requests
import threading
import time
from datetime import datetime
from collections import defaultdict

class SyncManager:
    """Synchronization system for distributed network"""
    
    def __init__(self, node_id="node1"):
        self.node_id = node_id
        self.peers = []
        self.last_sync_time = None
        self.sync_interval = 10  # seconds
        self.is_syncing = False
        self.sync_thread = None
        self.consensus_algorithm = "majority"  # majority, latest_timestamp, or blockchain
        
    def add_peer(self, peer_url):
        """Add peer for synchronization"""
        if peer_url not in self.peers:
            self.peers.append(peer_url)
            print(f"🔗 Peer added for sync: {peer_url}")
    
    def get_remote_devices(self, peer_url):
        """Fetch devices from remote peer"""
        try:
            response = requests.get(f"{peer_url}/api/network/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('devices', []), data.get('details', {})
        except Exception as e:
            print(f"Failed to fetch from {peer_url}: {e}")
        return [], {}
    
    def sync_with_peer(self, peer_url, local_devices):
        """Synchronize with a single peer"""
        remote_devices, remote_details = self.get_remote_devices(peer_url)
        
        merged_devices = local_devices.copy()
        conflicts = []
        
        # Merge remote devices
        for vid, device in remote_details.items():
            if vid not in merged_devices:
                # New device - add it
                merged_devices[vid] = device
                print(f"🆕 Added device from peer: {vid}")
            else:
                # Conflict - device exists in both
                local_time = merged_devices[vid].get('registration_time', '')
                remote_time = device.get('registration_time', '')
                conflicts.append({
                    'virtual_id': vid,
                    'local_time': local_time,
                    'remote_time': remote_time,
                    'local_device': merged_devices[vid],
                    'remote_device': device
                })
        
        # Resolve conflicts
        resolved = self.resolve_conflicts(conflicts)
        for resolution in resolved:
            merged_devices[resolution['virtual_id']] = resolution['device']
        
        return merged_devices, len(remote_devices), len(conflicts)
    
    def resolve_conflicts(self, conflicts):
        """Resolve conflicts using consensus algorithm"""
        resolved = []
        
        for conflict in conflicts:
            if self.consensus_algorithm == "majority":
                # Majority vote (requires more than 2 peers)
                resolved_device = self.majority_vote(conflict)
            elif self.consensus_algorithm == "latest_timestamp":
                # Last Write Wins (LWW)
                resolved_device = self.latest_timestamp_wins(conflict)
            else:
                # Default: keep both? Actually overwrite with latest
                resolved_device = self.latest_timestamp_wins(conflict)
            
            resolved.append({
                'virtual_id': conflict['virtual_id'],
                'device': resolved_device,
                'resolution_method': self.consensus_algorithm
            })
        
        return resolved
    
    def latest_timestamp_wins(self, conflict):
        """Last Write Wins - keep the latest timestamp"""
        local_time = datetime.fromisoformat(conflict['local_time']) if conflict['local_time'] != 'N/A' else datetime.min
        remote_time = datetime.fromisoformat(conflict['remote_time']) if conflict['remote_time'] != 'N/A' else datetime.min
        
        if remote_time > local_time:
            print(f"📝 Conflict resolved: {conflict['virtual_id']} - Remote wins (newer)")
            return conflict['remote_device']
        else:
            print(f"📝 Conflict resolved: {conflict['virtual_id']} - Local wins (newer)")
            return conflict['local_device']
    
    def majority_vote(self, conflict):
        """Majority vote - need to query all peers"""
        # This requires collecting votes from all peers
        # Simplified: return remote if more than half peers have it
        return conflict['remote_device']  # Simplified
    
    def sync_all_peers(self, local_devices_getter, local_devices_setter):
        """Synchronize with all peers"""
        if self.is_syncing:
            print("Sync already in progress")
            return
        
        self.is_syncing = True
        print(f"\n🔄 STARTING SYNCHRONIZATION WITH {len(self.peers)} PEERS")
        print("="*50)
        
        current_devices = local_devices_getter()
        merged_devices = current_devices.copy()
        
        total_new = 0
        total_conflicts = 0
        
        for peer in self.peers:
            print(f"\n📡 Syncing with {peer}...")
            merged, new_count, conflict_count = self.sync_with_peer(peer, merged_devices)
            merged_devices = merged
            total_new += new_count
            total_conflicts += conflict_count
        
        # Update local devices
        if len(merged_devices) > len(current_devices):
            local_devices_setter(merged_devices)
            print(f"\n✅ SYNC COMPLETE:")
            print(f"   New devices: {total_new}")
            print(f"   Conflicts resolved: {total_conflicts}")
            print(f"   Total devices: {len(merged_devices)}")
        else:
            print(f"\n✅ SYNC COMPLETE: No changes detected")
        
        self.last_sync_time = datetime.now()
        self.is_syncing = False
        
        return {
            'new_devices': total_new,
            'conflicts': total_conflicts,
            'total_devices': len(merged_devices),
            'sync_time': self.last_sync_time.isoformat()
        }
    
    def start_auto_sync(self, local_devices_getter, local_devices_setter, interval_seconds=None):
        """Start automatic periodic synchronization"""
        if interval_seconds:
            self.sync_interval = interval_seconds
        
        if self.sync_thread and self.sync_thread.is_alive():
            print("Auto sync already running")
            return
        
        def sync_worker():
            while True:
                time.sleep(self.sync_interval)
                if self.peers:
                    self.sync_all_peers(local_devices_getter, local_devices_setter)
        
        self.sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self.sync_thread.start()
        print(f"✅ Auto sync started (every {self.sync_interval} seconds)")
    
    def get_sync_status(self):
        """Get synchronization status"""
        return {
            'node_id': self.node_id,
            'peer_count': len(self.peers),
            'peers': self.peers,
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_interval': self.sync_interval,
            'consensus_algorithm': self.consensus_algorithm
        }
    
    # ============== LATENCY TESTING FUNCTIONS ==============
    
    def test_sync_latency(self, num_tests=20):
        """
        Test synchronization latency with all peers
        Measures time to sync with each peer
        """
        if not self.peers:
            return {
                'error': 'No peers available for latency test',
                'peer_count': 0
            }
        
        results = []
        
        for peer in self.peers:
            peer_latencies = []
            
            for i in range(num_tests):
                start_time = time.perf_counter()
                try:
                    response = requests.get(f"{peer}/api/network/status", timeout=5)
                    end_time = time.perf_counter()
                    
                    if response.status_code == 200:
                        latency_ms = (end_time - start_time) * 1000
                        peer_latencies.append(latency_ms)
                except Exception as e:
                    print(f"Latency test failed for {peer}: {e}")
                
                time.sleep(0.1)  # Small delay between tests
            
            if peer_latencies:
                import statistics as stat_lib
                results.append({
                    'peer': peer,
                    'average_latency_ms': round(stat_lib.mean(peer_latencies), 2),
                    'min_latency_ms': round(min(peer_latencies), 2),
                    'max_latency_ms': round(max(peer_latencies), 2),
                    'std_dev_ms': round(stat_lib.stdev(peer_latencies), 2) if len(peer_latencies) > 1 else 0,
                    'successful_tests': len(peer_latencies),
                    'total_tests': num_tests
                })
            else:
                results.append({
                    'peer': peer,
                    'error': 'No successful connections',
                    'successful_tests': 0,
                    'total_tests': num_tests
                })
        
        # Calculate overall average
        valid_results = [r for r in results if 'average_latency_ms' in r]
        if valid_results:
            overall_avg = sum(r['average_latency_ms'] for r in valid_results) / len(valid_results)
        else:
            overall_avg = 0
        
        return {
            'test_type': 'sync_latency',
            'peer_results': results,
            'summary': {
                'total_peers': len(self.peers),
                'successful_peers': len(valid_results),
                'overall_average_latency_ms': round(overall_avg, 2),
                'consensus_algorithm': self.consensus_algorithm
            }
        }
    
    def test_sync_complete_time(self, local_devices_getter, local_devices_setter, num_syncs=5):
        """
        Test complete sync operation time
        Measures total time to sync all peers
        """
        if not self.peers:
            return {'error': 'No peers available', 'peer_count': 0}
        
        sync_times = []
        
        for i in range(num_syncs):
            start_time = time.perf_counter()
            result = self.sync_all_peers(local_devices_getter, local_devices_setter)
            end_time = time.perf_counter()
            
            sync_time_ms = (end_time - start_time) * 1000
            sync_times.append(sync_time_ms)
            
            print(f"Sync {i+1} completed in {sync_time_ms:.2f}ms")
            time.sleep(2)  # Delay between syncs
        
        import statistics as stat_lib
        return {
            'test_type': 'sync_complete_time',
            'num_syncs': num_syncs,
            'peer_count': len(self.peers),
            'average_sync_time_ms': round(stat_lib.mean(sync_times), 2),
            'min_sync_time_ms': round(min(sync_times), 2),
            'max_sync_time_ms': round(max(sync_times), 2),
            'std_dev_ms': round(stat_lib.stdev(sync_times), 2) if len(sync_times) > 1 else 0,
            'individual_times_ms': [round(t, 2) for t in sync_times]
        }
    
    def test_conflict_resolution_time(self, num_conflicts=10):
        """
        Test time to resolve conflicts using different algorithms
        """
        # Create test conflicts
        test_conflicts = []
        for i in range(num_conflicts):
            test_conflicts.append({
                'virtual_id': f'TEST_VID_{i}',
                'local_time': datetime.now().isoformat(),
                'remote_time': datetime.now().isoformat(),
                'local_device': {'device_id': f'local_{i}'},
                'remote_device': {'device_id': f'remote_{i}'}
            })
        
        results = {}
        
        # Test each consensus algorithm
        algorithms = ['majority', 'latest_timestamp']
        
        for algo in algorithms:
            self.consensus_algorithm = algo
            start_time = time.perf_counter()
            resolved = self.resolve_conflicts(test_conflicts)
            end_time = time.perf_counter()
            resolution_time_ms = (end_time - start_time) * 1000
            
            results[algo] = {
                'resolution_time_ms': round(resolution_time_ms, 2),
                'conflicts_resolved': len(resolved),
                'algorithm': algo
            }
        
        return {
            'test_type': 'conflict_resolution_time',
            'num_conflicts': num_conflicts,
            'results': results,
            'fastest_algorithm': min(results.keys(), key=lambda x: results[x]['resolution_time_ms']) if results else None
        }
    
    def test_peer_discovery_latency(self, discovery_urls=[]):
        """
        Test peer discovery latency
        """
        if not discovery_urls:
            return {'error': 'No discovery URLs provided'}
        
        results = []
        
        for url in discovery_urls:
            latencies = []
            
            for i in range(5):
                start_time = time.perf_counter()
                try:
                    response = requests.get(f"{url}/api/peers", timeout=5)
                    end_time = time.perf_counter()
                    
                    if response.status_code == 200:
                        latency_ms = (end_time - start_time) * 1000
                        latencies.append(latency_ms)
                except Exception as e:
                    print(f"Discovery failed for {url}: {e}")
                
                time.sleep(0.5)
            
            if latencies:
                import statistics as stat_lib
                results.append({
                    'discovery_url': url,
                    'average_latency_ms': round(stat_lib.mean(latencies), 2),
                    'min_latency_ms': round(min(latencies), 2),
                    'max_latency_ms': round(max(latencies), 2),
                    'successful_tests': len(latencies)
                })
        
        return {
            'test_type': 'peer_discovery_latency',
            'results': results,
            'summary': {
                'total_discovery_urls': len(discovery_urls),
                'successful_urls': len([r for r in results if 'average_latency_ms' in r])
            }
        }
    
    def run_all_sync_tests(self, local_devices_getter=None, local_devices_setter=None):
        """
        Run all synchronization latency tests
        """
        print("\n" + "="*50)
        print("🧪 Running Synchronization Latency Tests")
        print("="*50)
        
        results = {
            'sync_latency': self.test_sync_latency(),
            'conflict_resolution': self.test_conflict_resolution_time(),
            'sync_status': self.get_sync_status(),
            'timestamp': time.time()
        }
        
        # Only run complete sync test if getter/setter provided
        if local_devices_getter and local_devices_setter and self.peers:
            results['sync_complete_time'] = self.test_sync_complete_time(local_devices_getter, local_devices_setter)
        
        print("\n✅ All sync latency tests completed!")
        return results
    
    def get_sync_metrics(self):
        """Get all sync metrics at once"""
        return {
            'sync_latency': self.test_sync_latency(),
            'conflict_resolution': self.test_conflict_resolution_time(),
            'sync_status': self.get_sync_status()
        }