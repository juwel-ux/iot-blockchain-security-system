# network_layer/propagation.py
import json
import requests
import threading
import time
import paho.mqtt.client as mqtt
from datetime import datetime

class PropagationManager:
    """Distributed propagation system for Network Layer"""
    
    def __init__(self, node_id="node1"):
        self.node_id = node_id
        self.peer_nodes = []
        self.peer_discovery_urls = []
        self.mqtt_client = None
        self.gossip_enabled = True
        
    def add_peer(self, peer_url):
        """Add a peer node to the network"""
        if peer_url not in self.peer_nodes:
            self.peer_nodes.append(peer_url)
            print(f"✅ Peer added: {peer_url}")
            return True
        return False
    
    def remove_peer(self, peer_url):
        """Remove a peer node from the network"""
        if peer_url in self.peer_nodes:
            self.peer_nodes.remove(peer_url)
            print(f"❌ Peer removed: {peer_url}")
            return True
        return False
    
    def get_peers(self):
        """Get all peer nodes"""
        return self.peer_nodes
    
    def discover_peers(self, discovery_urls):
        """Discover peers from discovery service"""
        discovered = []
        
        for url in discovery_urls:
            try:
                response = requests.get(f"{url}/api/peers", timeout=5)
                peers = response.json().get('peers', [])
                discovered.extend(peers)
                print(f"🔍 Discovered {len(peers)} peers from {url}")
            except Exception as e:
                print(f"Failed to discover from {url}: {e}")
        
        for peer in discovered:
            self.add_peer(peer)
        
        return discovered
    
    def propagate_via_mqtt(self, device_data, topic="network/registrations"):
        """Propagate device registration via MQTT"""
        if not self.mqtt_client:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect("localhost", 1883, 60)
            self.mqtt_client.loop_start()
        
        try:
            payload = json.dumps({
                'source_node': self.node_id,
                'timestamp': datetime.now().isoformat(),
                'data': device_data
            })
            self.mqtt_client.publish(topic, payload)
            print(f"📡 Propagated via MQTT: {topic}")
            return True
        except Exception as e:
            print(f"❌ MQTT propagation failed: {e}")
            return False
    
    def propagate_via_http(self, device_data):
        """Propagate to all peers via HTTP POST"""
        success_count = 0
        
        for peer in self.peer_nodes:
            try:
                response = requests.post(
                    f"{peer}/api/network/sync",
                    json=device_data,
                    timeout=5
                )
                if response.status_code == 200:
                    success_count += 1
                    print(f"✅ Synced with {peer}")
                else:
                    print(f"⚠️ Failed to sync with {peer}: {response.status_code}")
            except Exception as e:
                print(f"❌ Could not reach {peer}: {e}")
        
        print(f"📊 Propagation complete: {success_count}/{len(self.peer_nodes)} peers synced")
        return success_count
    
    def propagate_via_gossip(self, device_data, ttl=3):
        """Gossip protocol propagation"""
        if ttl <= 0:
            return
        
        print(f"🗣️ Gossip propagating (TTL={ttl})")
        
        import random
        gossip_peers = random.sample(self.peer_nodes, min(3, len(self.peer_nodes)))
        
        for peer in gossip_peers:
            try:
                response = requests.post(
                    f"{peer}/api/network/gossip",
                    json={
                        'data': device_data,
                        'ttl': ttl - 1,
                        'source': self.node_id
                    },
                    timeout=3
                )
                if response.status_code == 200:
                    print(f"🗣️ Gossip sent to {peer}")
            except:
                pass
    
    def broadcast_to_all(self, device_data):
        """Broadcast to all propagation channels"""
        print(f"\n📢 BROADCASTING DEVICE REGISTRATION")
        print(f"   Virtual ID: {device_data.get('virtual_id', 'N/A')}")
        
        http_count = self.propagate_via_http(device_data)
        mqtt_success = self.propagate_via_mqtt(device_data)
        
        if self.gossip_enabled:
            self.propagate_via_gossip(device_data)
        
        return {
            'http_peers': http_count,
            'mqtt': mqtt_success,
            'total_peers': len(self.peer_nodes)
        }
    
    def get_network_status(self):
        """Get current network status"""
        return {
            'node_id': self.node_id,
            'peer_count': len(self.peer_nodes),
            'peers': self.peer_nodes,
            'gossip_enabled': self.gossip_enabled
        }
    
    # ============== TESTING FUNCTIONS FOR PROPAGATION ==============
    
    def test_propagation_delay(self, num_tests=10):
        """Test 1: Measure propagation delay to peers"""
        delays = []
        
        for i in range(num_tests):
            test_data = {
                'test_id': i,
                'virtual_id': f'TEST_VID_{i}',
                'timestamp': time.time()
            }
            
            for peer in self.peer_nodes:
                try:
                    start = time.perf_counter()
                    response = requests.post(
                        f"{peer}/api/network/sync",
                        json=test_data,
                        timeout=5
                    )
                    end = time.perf_counter()
                    if response.status_code == 200:
                        delay_ms = (end - start) * 1000
                        delays.append(delay_ms)
                except:
                    pass
            
            time.sleep(0.1)
        
        if delays:
            avg_delay = sum(delays) / len(delays)
            return {
                'average_delay_ms': round(avg_delay, 2),
                'min_delay_ms': round(min(delays), 2),
                'max_delay_ms': round(max(delays), 2),
                'total_tests': len(delays),
                'peer_count': len(self.peer_nodes)
            }
        return {
            'average_delay_ms': 0,
            'total_tests': 0,
            'peer_count': len(self.peer_nodes),
            'message': 'No peers available'
        }
    
    def test_peer_sync_time(self):
        """Test 2: Measure time to sync with all peers"""
        results = []
        
        for peer in self.peer_nodes:
            start = time.time()
            try:
                response = requests.get(f"{peer}/api/network/status", timeout=5)
                if response.status_code == 200:
                    sync_time = (time.time() - start) * 1000
                    results.append({
                        'peer': peer,
                        'sync_time_ms': round(sync_time, 2),
                        'status': 'success'
                    })
                else:
                    results.append({'peer': peer, 'status': 'failed'})
            except:
                results.append({'peer': peer, 'status': 'failed'})
        
        successful = [r for r in results if r.get('status') == 'success']
        sync_times = [r['sync_time_ms'] for r in successful if 'sync_time_ms' in r]
        
        return {
            'total_peers': len(self.peer_nodes),
            'successful_sync': len(successful),
            'failed_sync': len(self.peer_nodes) - len(successful),
            'average_sync_time_ms': round(sum(sync_times) / len(sync_times), 2) if sync_times else 0,
            'details': results
        }
    
    def test_gossip_coverage(self, initial_ttl=3):
        """Test 3: Measure gossip protocol coverage"""
        if not self.peer_nodes:
            return {'coverage': 0, 'message': 'No peers available'}
        
        reached_peers = set()
        
        def simulate_gossip(current_node, ttl, path):
            if ttl <= 0 or current_node in reached_peers:
                return
            reached_peers.add(current_node)
            
            import random
            neighbors = random.sample(self.peer_nodes, min(2, len(self.peer_nodes)))
            for neighbor in neighbors:
                if neighbor not in path:
                    simulate_gossip(neighbor, ttl - 1, path + [current_node])
        
        simulate_gossip(self.node_id, initial_ttl, [])
        
        coverage_percent = (len(reached_peers) / (len(self.peer_nodes) + 1)) * 100
        
        return {
            'coverage_percentage': round(coverage_percent, 2),
            'reached_peers': len(reached_peers),
            'total_peers': len(self.peer_nodes) + 1,
            'initial_ttl': initial_ttl
        }
    
    def test_broadcast_reliability(self, num_broadcasts=10):
        """Test 4: Measure broadcast reliability"""
        results = []
        successful = 0
        
        for i in range(num_broadcasts):
            test_data = {
                'test_id': i,
                'virtual_id': f'BROADCAST_TEST_{i}',
                'timestamp': time.time()
            }
            
            result = self.broadcast_to_all(test_data)
            if result['http_peers'] > 0 or result['mqtt']:
                successful += 1
            results.append(result)
            time.sleep(0.2)
        
        reliability_percent = (successful / num_broadcasts) * 100
        
        return {
            'reliability_percentage': round(reliability_percent, 2),
            'successful_broadcasts': successful,
            'total_broadcasts': num_broadcasts,
            'average_http_peers': sum(r['http_peers'] for r in results) / num_broadcasts if results else 0,
            'details': results
        }
    
    def get_propagation_metrics(self):
        """Get all propagation test metrics at once"""
        return {
            'propagation_delay': self.test_propagation_delay(),
            'peer_sync_time': self.test_peer_sync_time(),
            'gossip_coverage': self.test_gossip_coverage(),
            'broadcast_reliability': self.test_broadcast_reliability(),
            'network_status': self.get_network_status()
        }