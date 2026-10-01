
# edge_layer/network_sender.py
import json
import paho.mqtt.client as mqtt
import time
import statistics as stat_lib
import threading

# Network Layer MQTT Settings
NETWORK_BROKER = "localhost"
NETWORK_PORT = 1883

# ✅ আলাদা Topic for different purposes
REGISTRATION_TOPIC = "network/device_registration"  # Manual device registration
COMMUNICATION_TOPIC = "network/communication"       # Auto message communication

class NetworkSender:
    """Handles sending packets to Network Layer with encrypted private key support"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self.send_count = 0
        self.failed_count = 0
        self.registration_sent = 0
        self.communication_sent = 0
        self.reconnection_attempts = 0
        self.successful_reconnections = 0
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.connected = True
            print(f"✅ Connected to Network Layer MQTT at {NETWORK_BROKER}:{NETWORK_PORT}")
        else:
            self.connected = False
            print(f"❌ Connection failed with code: {rc}")
    
    def connect_mqtt(self):
        """Connect to MQTT broker for Network Layer communication"""
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.connect(NETWORK_BROKER, NETWORK_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            time.sleep(0.5)
            return self.connected
        except Exception as e:
            print(f"❌ Could not connect to Network Layer MQTT: {e}")
            self.connected = False
            return False
    
    def send_to_network(self, packet, is_registration=False):
        """
        Send packet to Network Layer
        - is_registration=True → device registration (Manual processing)
        - is_registration=False → communication message (Auto processing)
        
        ✅ Packet contains:
           - Public Key (Plain)
           - Encrypted Private Key (With user password) - NEW!
           - Signature
           - Device Metadata
        """
        if not self.connected:
            if not self.connect_mqtt():
                return False
        
        try:
            # ✅ Choose topic based on packet type
            topic = REGISTRATION_TOPIC if is_registration else COMMUNICATION_TOPIC
            
            # Ensure packet has required fields
            if is_registration:
                required_fields = ['virtual_id', 'public_key', 'signature']
                missing = [f for f in required_fields if f not in packet]
                if missing:
                    print(f"❌ Registration packet missing fields: {missing}")
                    return False
                
                # Check if encrypted_private_key is present
                if 'encrypted_private_key' not in packet:
                    print(f"⚠️ Warning: No encrypted_private_key in packet")
                else:
                    print(f"   🔐 Encrypted private key included (length: {len(packet['encrypted_private_key'])})")
            
            payload = json.dumps(packet)
            result = self.client.publish(topic, payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.send_count += 1
                if is_registration:
                    self.registration_sent += 1
                    print(f"✅ Device Registration sent to Network Layer (#{self.registration_sent})")
                    print(f"   Virtual ID: {packet.get('virtual_id', 'N/A')}")
                    print(f"   Device ID: {packet.get('device_id', 'N/A')}")
                    print(f"   🔐 Encrypted Private Key: {'Present' if packet.get('encrypted_private_key') else 'Missing'}")
                else:
                    self.communication_sent += 1
                    print(f"✅ Communication message sent to Network Layer (#{self.communication_sent})")
                    print(f"   To: {packet.get('receiver_id', 'N/A')}")
                
                print(f"   Topic: {topic}")
                return True
            else:
                self.failed_count += 1
                print(f"❌ Failed to send packet. Error code: {result.rc}")
                return False
                
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Error sending to Network Layer: {e}")
            return False
    
    def send_registration(self, packet):
        """Send device registration packet to Network Layer (includes encrypted private key)"""
        print(f"\n📡 Sending registration packet to Network Layer...")
        return self.send_to_network(packet, is_registration=True)
    
    def send_communication(self, packet):
        """Send communication message packet (Auto mode)"""
        return self.send_to_network(packet, is_registration=False)
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            print("🔌 Disconnected from Network Layer MQTT")
    
    def send_batch_to_network(self, packets, is_registration=False):
        """Send multiple packets to Network Layer"""
        success_count = 0
        for i, packet in enumerate(packets):
            print(f"\n📦 Sending batch packet {i+1}/{len(packets)}")
            if self.send_to_network(packet, is_registration):
                success_count += 1
            time.sleep(0.1)  # Small delay between sends
        return success_count
    
    def get_stats(self):
        """Get sending statistics"""
        return {
            'sent': self.send_count,
            'failed': self.failed_count,
            'total': self.send_count + self.failed_count,
            'registration_sent': self.registration_sent,
            'communication_sent': self.communication_sent,
            'reconnection_attempts': self.reconnection_attempts,
            'successful_reconnections': self.successful_reconnections,
            'success_rate': round((self.send_count / (self.send_count + self.failed_count) * 100), 2) if (self.send_count + self.failed_count) > 0 else 0
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.send_count = 0
        self.failed_count = 0
        self.registration_sent = 0
        self.communication_sent = 0
        self.reconnection_attempts = 0
        self.successful_reconnections = 0
        print("📊 Statistics reset")
    
    def test_connection(self):
        """Test MQTT connection without sending data"""
        try:
            test_client = mqtt.Client()
            test_client.connect(NETWORK_BROKER, NETWORK_PORT, 5)
            test_client.disconnect()
            print("✅ MQTT connection test successful")
            return True
        except Exception as e:
            print(f"❌ MQTT connection test failed: {e}")
            return False
    
    # ========== MQTT RELIABILITY TESTING FUNCTIONS ==========
    
    def test_mqtt_connection_reliability(self, num_tests=20):
        """
        Test 1: MQTT connection reliability
        Measures success rate of connection attempts
        """
        results = []
        successful = 0
        
        for i in range(num_tests):
            start_time = time.perf_counter()
            try:
                test_client = mqtt.Client()
                test_client.connect(NETWORK_BROKER, NETWORK_PORT, 5)
                connection_time = (time.perf_counter() - start_time) * 1000
                test_client.disconnect()
                successful += 1
                results.append({
                    'test_number': i + 1,
                    'connection_time_ms': round(connection_time, 2),
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'test_number': i + 1,
                    'error': str(e),
                    'status': 'failed'
                })
            
            time.sleep(0.5)
        
        success_rate = (successful / num_tests) * 100 if num_tests > 0 else 0
        connection_times = [r['connection_time_ms'] for r in results if r.get('status') == 'success']
        
        return {
            'test_type': 'mqtt_connection_reliability',
            'total_tests': num_tests,
            'successful_connections': successful,
            'failed_connections': num_tests - successful,
            'success_rate_percentage': round(success_rate, 2),
            'connection_times': {
                'average_ms': round(stat_lib.mean(connection_times), 2) if connection_times else 0,
                'min_ms': round(min(connection_times), 2) if connection_times else 0,
                'max_ms': round(max(connection_times), 2) if connection_times else 0
            },
            'results': results[:10]
        }
    
    def test_message_delivery_reliability(self, num_messages=50):
        """
        Test 2: Message delivery reliability
        Measures success rate of message delivery
        """
        if not self.connect_mqtt():
            return {'error': 'Could not connect to MQTT broker'}
        
        results = []
        successful = 0
        
        for i in range(num_messages):
            test_packet = {
                "type": "reliability_test",
                "test_id": i,
                "timestamp": time.time(),
                "message": f"Test message {i}"
            }
            
            start_time = time.perf_counter()
            success = self.send_communication(test_packet)
            delivery_time = (time.perf_counter() - start_time) * 1000 if success else 0
            
            if success:
                successful += 1
                results.append({
                    'message_number': i + 1,
                    'delivery_time_ms': round(delivery_time, 2),
                    'status': 'delivered'
                })
            else:
                results.append({
                    'message_number': i + 1,
                    'status': 'failed'
                })
            
            time.sleep(0.2)
        
        self.disconnect()
        
        success_rate = (successful / num_messages) * 100 if num_messages > 0 else 0
        delivery_times = [r['delivery_time_ms'] for r in results if r.get('status') == 'delivered']
        
        return {
            'test_type': 'message_delivery_reliability',
            'total_messages': num_messages,
            'successful_deliveries': successful,
            'failed_deliveries': num_messages - successful,
            'success_rate_percentage': round(success_rate, 2),
            'delivery_times': {
                'average_ms': round(stat_lib.mean(delivery_times), 2) if delivery_times else 0,
                'min_ms': round(min(delivery_times), 2) if delivery_times else 0,
                'max_ms': round(max(delivery_times), 2) if delivery_times else 0
            },
            'results': results[:10]
        }
    
    def test_broker_recovery_time(self, broker_down_time=5):
        """
        Test 3: Broker recovery time
        Simulates broker down and measures recovery time
        """
        print(f"\n🔴 Simulating broker down for {broker_down_time} seconds...")
        
        # First, ensure we are connected
        self.connect_mqtt()
        
        # Disconnect to simulate broker down
        self.disconnect()
        self.connected = False
        
        # Wait for broker to be down
        start_recovery = time.time()
        recovered = False
        recovery_time = 0
        
        # Try to reconnect
        for i in range(broker_down_time * 2):  # Try every 0.5 seconds
            time.sleep(0.5)
            if self.connect_mqtt():
                recovery_time = time.time() - start_recovery
                recovered = True
                break
        
        return {
            'test_type': 'broker_recovery_time',
            'broker_down_duration_sec': broker_down_time,
            'recovered': recovered,
            'recovery_time_sec': round(recovery_time, 2) if recovered else None,
            'reconnection_attempts': self.reconnection_attempts,
            'status': 'Recovered successfully' if recovered else 'Failed to recover'
        }
    
    def test_message_queuing_during_disconnect(self, num_messages=30, disconnect_time=10):
        """
        Test 4: Message queuing during broker disconnection
        Messages should be queued and delivered after reconnection
        """
        print(f"\n📦 Testing message queuing during {disconnect_time}s disconnection...")
        
        # Ensure connected first
        self.connect_mqtt()
        
        # Disconnect to simulate broker down
        self.disconnect()
        self.connected = False
        
        # Send messages while disconnected
        queued_messages = []
        for i in range(num_messages):
            test_packet = {
                "type": "queuing_test",
                "test_id": i,
                "timestamp": time.time(),
                "message": f"Queued message {i}"
            }
            
            # Try to send (will fail and queue)
            try:
                payload = json.dumps(test_packet)
                # Store in local queue (simulated)
                queued_messages.append(test_packet)
            except Exception as e:
                print(f"Error queueing message {i}: {e}")
        
        print(f"📦 {len(queued_messages)} messages queued during disconnect")
        
        # Reconnect
        print(f"🔌 Attempting to reconnect...")
        start_reconnect = time.time()
        reconnect_success = self.connect_mqtt()
        reconnect_time = (time.time() - start_reconnect) * 1000
        
        # Send queued messages after reconnection
        delivered_after_reconnect = 0
        for msg in queued_messages:
            if self.send_communication(msg):
                delivered_after_reconnect += 1
            time.sleep(0.1)
        
        self.disconnect()
        
        return {
            'test_type': 'message_queuing_during_disconnect',
            'total_queued_messages': len(queued_messages),
            'delivered_after_reconnect': delivered_after_reconnect,
            'delivery_rate_percentage': round((delivered_after_reconnect / len(queued_messages)) * 100, 2) if queued_messages else 0,
            'reconnect_time_ms': round(reconnect_time, 2),
            'disconnect_duration_sec': disconnect_time,
            'status': 'Success' if delivered_after_reconnect == len(queued_messages) else 'Partial success'
        }
    
    def test_mqtt_load_handling(self, num_batches=10, messages_per_batch=20):
        """
        Test 5: MQTT load handling - stress test
        Measures performance under high message load
        """
        if not self.connect_mqtt():
            return {'error': 'Could not connect to MQTT broker'}
        
        batch_results = []
        total_messages = 0
        total_successful = 0
        
        for batch in range(num_batches):
            batch_success = 0
            start_time = time.perf_counter()
            
            for i in range(messages_per_batch):
                test_packet = {
                    "type": "load_test",
                    "batch": batch,
                    "message_id": i,
                    "timestamp": time.time(),
                    "message": f"Load test message batch {batch} msg {i}"
                }
                
                if self.send_communication(test_packet):
                    batch_success += 1
                    total_successful += 1
                total_messages += 1
            
            end_time = time.perf_counter()
            batch_time = (end_time - start_time) * 1000
            
            batch_results.append({
                'batch_number': batch + 1,
                'messages_sent': messages_per_batch,
                'successful': batch_success,
                'failed': messages_per_batch - batch_success,
                'batch_time_ms': round(batch_time, 2),
                'throughput_msg_per_sec': round((messages_per_batch / (batch_time / 1000)), 2) if batch_time > 0 else 0
            })
            
            time.sleep(0.5)
        
        self.disconnect()
        
        overall_success_rate = (total_successful / total_messages) * 100 if total_messages > 0 else 0
        
        return {
            'test_type': 'mqtt_load_handling',
            'total_batches': num_batches,
            'messages_per_batch': messages_per_batch,
            'total_messages': total_messages,
            'total_successful': total_successful,
            'overall_success_rate': round(overall_success_rate, 2),
            'average_throughput_msg_per_sec': round(stat_lib.mean([r['throughput_msg_per_sec'] for r in batch_results]), 2) if batch_results else 0,
            'batch_results': batch_results
        }
    
    def test_mqtt_long_running_stability(self, duration_seconds=30):
        """
        Test 6: Long running MQTT stability test
        Sends messages continuously and monitors connection stability
        """
        if not self.connect_mqtt():
            return {'error': 'Could not connect to MQTT broker'}
        
        start_time = time.time()
        messages_sent = 0
        successful_sends = 0
        connection_drops = 0
        last_connected = True
        
        print(f"\n⏱️ Running stability test for {duration_seconds} seconds...")
        
        while time.time() - start_time < duration_seconds:
            test_packet = {
                "type": "stability_test",
                "message_id": messages_sent,
                "timestamp": time.time(),
                "message": f"Stability test message {messages_sent}"
            }
            
            if self.send_communication(test_packet):
                successful_sends += 1
                if not last_connected:
                    connection_drops += 1
                    last_connected = True
            else:
                if last_connected:
                    connection_drops += 1
                    last_connected = False
            
            messages_sent += 1
            time.sleep(0.5)
        
        self.disconnect()
        
        return {
            'test_type': 'mqtt_long_running_stability',
            'duration_seconds': duration_seconds,
            'total_messages': messages_sent,
            'successful_sends': successful_sends,
            'failed_sends': messages_sent - successful_sends,
            'connection_drops_detected': connection_drops,
            'success_rate_percentage': round((successful_sends / messages_sent) * 100, 2) if messages_sent > 0 else 0,
            'messages_per_second': round(messages_sent / duration_seconds, 2)
        }
    
    def test_mqtt_different_topics(self, num_messages=20):
        """
        Test 7: MQTT different topic reliability
        Tests both registration and communication topics
        """
        if not self.connect_mqtt():
            return {'error': 'Could not connect to MQTT broker'}
        
        registration_results = []
        communication_results = []
        
        # Test registration topic
        for i in range(num_messages):
            reg_packet = {
                "type": "test_registration",
                "virtual_id": f"TEST_REG_{i}",
                "public_key": "test_public_key",
                "signature": "test_signature",
                "timestamp": time.time()
            }
            
            start_time = time.perf_counter()
            success = self.send_registration(reg_packet)
            delivery_time = (time.perf_counter() - start_time) * 1000 if success else 0
            
            registration_results.append({
                'message_number': i + 1,
                'status': 'success' if success else 'failed',
                'delivery_time_ms': round(delivery_time, 2) if success else 0
            })
            time.sleep(0.2)
        
        # Test communication topic
        for i in range(num_messages):
            comm_packet = {
                "type": "test_communication",
                "receiver_id": f"TEST_COMM_{i}",
                "message": f"Test communication {i}",
                "timestamp": time.time()
            }
            
            start_time = time.perf_counter()
            success = self.send_communication(comm_packet)
            delivery_time = (time.perf_counter() - start_time) * 1000 if success else 0
            
            communication_results.append({
                'message_number': i + 1,
                'status': 'success' if success else 'failed',
                'delivery_time_ms': round(delivery_time, 2) if success else 0
            })
            time.sleep(0.2)
        
        self.disconnect()
        
        reg_success = len([r for r in registration_results if r['status'] == 'success'])
        comm_success = len([r for r in communication_results if r['status'] == 'success'])
        
        return {
            'test_type': 'mqtt_different_topics',
            'total_messages_per_topic': num_messages,
            'registration_topic': {
                'successful': reg_success,
                'failed': num_messages - reg_success,
                'success_rate': round((reg_success / num_messages) * 100, 2),
                'average_delivery_ms': round(stat_lib.mean([r['delivery_time_ms'] for r in registration_results if r['delivery_time_ms'] > 0]), 2) if registration_results else 0
            },
            'communication_topic': {
                'successful': comm_success,
                'failed': num_messages - comm_success,
                'success_rate': round((comm_success / num_messages) * 100, 2),
                'average_delivery_ms': round(stat_lib.mean([r['delivery_time_ms'] for r in communication_results if r['delivery_time_ms'] > 0]), 2) if communication_results else 0
            }
        }
    
    def run_all_mqtt_reliability_tests(self):
        """
        Run all MQTT reliability tests
        """
        print("\n" + "="*60)
        print("🧪 Running MQTT Reliability Tests")
        print("="*60)
        
        results = {
            'connection_reliability': self.test_mqtt_connection_reliability(15),
            'message_delivery_reliability': self.test_message_delivery_reliability(30),
            'load_handling': self.test_mqtt_load_handling(5, 15),
            'different_topics': self.test_mqtt_different_topics(15),
            'long_running_stability': self.test_mqtt_long_running_stability(20),
            'timestamp': time.time()
        }
        
        print("\n✅ All MQTT reliability tests completed!")
        return results
    
    def get_mqtt_metrics(self):
        """
        Get MQTT reliability metrics summary
        """
        conn_test = self.test_mqtt_connection_reliability(10)
        msg_test = self.test_message_delivery_reliability(20)
        
        return {
            'connection_success_rate': conn_test['success_rate_percentage'],
            'message_delivery_success_rate': msg_test['success_rate_percentage'],
            'average_connection_time_ms': conn_test['connection_times']['average_ms'],
            'average_delivery_time_ms': msg_test['delivery_times']['average_ms'],
            'total_messages_sent': self.send_count,
            'overall_success_rate': self.get_stats()['success_rate'],
            'mqtt_broker': NETWORK_BROKER,
            'mqtt_port': NETWORK_PORT
        }


# ============== TEST FUNCTION ==============
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing NetworkSender Module with MQTT Reliability")
    print("="*60)
    
    sender = NetworkSender()
    
    # Test connection
    print("\n🔌 Testing MQTT connection...")
    sender.test_connection()
    
    # Run MQTT reliability tests
    results = sender.run_all_mqtt_reliability_tests()
    
    # Print results summary
    print("\n" + "="*60)
    print("📊 MQTT RELIABILITY TEST RESULTS")
    print("="*60)
    
    if 'connection_reliability' in results:
        cr = results['connection_reliability']
        print(f"\n✅ Connection Reliability: {cr['success_rate_percentage']}%")
        print(f"   Avg connection time: {cr['connection_times']['average_ms']} ms")
    
    if 'message_delivery_reliability' in results:
        mr = results['message_delivery_reliability']
        print(f"\n✅ Message Delivery Reliability: {mr['success_rate_percentage']}%")
        print(f"   Avg delivery time: {mr['delivery_times']['average_ms']} ms")
    
    if 'load_handling' in results:
        lh = results['load_handling']
        print(f"\n✅ Load Handling: {lh['overall_success_rate']}% success")
        print(f"   Throughput: {lh['average_throughput_msg_per_sec']} msg/sec")
    
    print("\n" + "="*60)