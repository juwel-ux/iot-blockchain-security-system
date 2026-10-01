# perception_layer/mqtt_handler.py
import json
import paho.mqtt.client as mqtt
import time
import statistics as stat_lib
import threading

BROKER = "localhost"
PORT = 1883
TOPIC = "device/registration"

# Global statistics for testing
mqtt_test_stats = {
    'total_published': 0,
    'successful_publishes': 0,
    'failed_publishes': 0,
    'connection_attempts': 0,
    'successful_connections': 0
}


def send_packet(packet):
    """Send registration packet via MQTT"""
    client = mqtt.Client()
    try:
        print(f"🔌 Connecting to MQTT broker at {BROKER}:{PORT}...")
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        
        # Wait a moment for connection to establish
        time.sleep(0.5)
        
        payload = json.dumps(packet)
        print(f"📤 Publishing to topic '{TOPIC}': {payload[:100]}...")
        result = client.publish(TOPIC, payload)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("✅ Packet published successfully")
            mqtt_test_stats['total_published'] += 1
            mqtt_test_stats['successful_publishes'] += 1
            time.sleep(0.5)
            client.loop_stop()
            client.disconnect()
            return True
        else:
            print(f"❌ Failed to publish. Error code: {result.rc}")
            mqtt_test_stats['total_published'] += 1
            mqtt_test_stats['failed_publishes'] += 1
            client.loop_stop()
            client.disconnect()
            return False
            
    except Exception as e:
        print(f"❌ MQTT Error: {e}")
        mqtt_test_stats['total_published'] += 1
        mqtt_test_stats['failed_publishes'] += 1
        return False


# ========== MQTT TESTING FUNCTIONS ==========

def test_mqtt_connection(num_tests=20):
    """
    Test 1: MQTT connection reliability
    Measures success rate and connection time
    """
    results = []
    successful = 0
    connection_times = []
    
    for i in range(num_tests):
        start_time = time.perf_counter()
        client = mqtt.Client()
        try:
            client.connect(BROKER, PORT, 5)
            connection_time = (time.perf_counter() - start_time) * 1000
            connection_times.append(connection_time)
            successful += 1
            results.append({
                'test_number': i + 1,
                'connection_time_ms': round(connection_time, 2),
                'status': 'success'
            })
            client.disconnect()
        except Exception as e:
            results.append({
                'test_number': i + 1,
                'error': str(e),
                'status': 'failed'
            })
        
        time.sleep(0.3)
    
    success_rate = (successful / num_tests) * 100 if num_tests > 0 else 0
    
    return {
        'test_type': 'mqtt_connection_reliability',
        'total_tests': num_tests,
        'successful_connections': successful,
        'failed_connections': num_tests - successful,
        'success_rate_percentage': round(success_rate, 2),
        'connection_times': {
            'average_ms': round(stat_lib.mean(connection_times), 2) if connection_times else 0,
            'min_ms': round(min(connection_times), 2) if connection_times else 0,
            'max_ms': round(max(connection_times), 2) if connection_times else 0,
            'std_dev_ms': round(stat_lib.stdev(connection_times), 2) if len(connection_times) > 1 else 0
        },
        'results': results[:10]
    }


def test_packet_publish_reliability(num_packets=30):
    """
    Test 2: Packet publish reliability
    Measures success rate of packet publishing
    """
    results = []
    successful = 0
    publish_times = []
    
    for i in range(num_packets):
        test_packet = {
            "device_id": f"TEST_DEVICE_{i}",
            "device_type": "test",
            "timestamp": time.time(),
            "test_message": f"Test packet number {i}"
        }
        
        start_time = time.perf_counter()
        success = send_packet(test_packet)
        publish_time = (time.perf_counter() - start_time) * 1000 if success else 0
        
        if success:
            successful += 1
            publish_times.append(publish_time)
            results.append({
                'packet_number': i + 1,
                'publish_time_ms': round(publish_time, 2),
                'status': 'success'
            })
        else:
            results.append({
                'packet_number': i + 1,
                'status': 'failed'
            })
        
        time.sleep(0.2)
    
    success_rate = (successful / num_packets) * 100 if num_packets > 0 else 0
    
    return {
        'test_type': 'packet_publish_reliability',
        'total_packets': num_packets,
        'successful_publishes': successful,
        'failed_publishes': num_packets - successful,
        'success_rate_percentage': round(success_rate, 2),
        'publish_times': {
            'average_ms': round(stat_lib.mean(publish_times), 2) if publish_times else 0,
            'min_ms': round(min(publish_times), 2) if publish_times else 0,
            'max_ms': round(max(publish_times), 2) if publish_times else 0
        },
        'results': results[:10]
    }


def test_mqtt_latency(num_tests=50):
    """
    Test 3: MQTT end-to-end latency
    Measures time from publish to receive
    """
    received_messages = []
    receive_times = []
    
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if 'send_time' in payload:
                receive_time = time.time()
                latency = (receive_time - payload['send_time']) * 1000
                received_messages.append({
                    'message_id': payload.get('message_id'),
                    'latency_ms': round(latency, 2)
                })
                receive_times.append(latency)
        except:
            pass
    
    # Setup subscriber
    sub_client = mqtt.Client()
    sub_client.on_message = on_message
    sub_client.connect(BROKER, PORT, 60)
    sub_client.subscribe(TOPIC)
    sub_client.loop_start()
    
    time.sleep(1)
    
    # Publish test messages
    pub_client = mqtt.Client()
    pub_client.connect(BROKER, PORT, 60)
    
    for i in range(num_tests):
        test_packet = {
            "device_id": f"LATENCY_TEST_{i}",
            "device_type": "latency_test",
            "send_time": time.time(),
            "message_id": i,
            "timestamp": time.time()
        }
        
        payload = json.dumps(test_packet)
        pub_client.publish(TOPIC, payload)
        time.sleep(0.2)
    
    # Wait for all messages to be received
    time.sleep(3)
    
    sub_client.loop_stop()
    sub_client.disconnect()
    pub_client.disconnect()
    
    return {
        'test_type': 'mqtt_latency',
        'total_messages': num_tests,
        'messages_received': len(received_messages),
        'receive_rate_percentage': round((len(received_messages) / num_tests) * 100, 2) if num_tests > 0 else 0,
        'latency': {
            'average_ms': round(stat_lib.mean(receive_times), 2) if receive_times else 0,
            'min_ms': round(min(receive_times), 2) if receive_times else 0,
            'max_ms': round(max(receive_times), 2) if receive_times else 0,
            'std_dev_ms': round(stat_lib.stdev(receive_times), 2) if len(receive_times) > 1 else 0
        },
        'results': received_messages[:10]
    }


def test_mqtt_load_handling(num_messages=100, batch_size=10):
    """
    Test 4: MQTT load handling under stress
    """
    results = []
    batch_results = []
    
    for batch in range(num_messages // batch_size):
        batch_success = 0
        start_time = time.perf_counter()
        
        for i in range(batch_size):
            test_packet = {
                "device_id": f"LOAD_TEST_{batch}_{i}",
                "device_type": "load_test",
                "timestamp": time.time(),
                "batch": batch,
                "message_num": i
            }
            
            if send_packet(test_packet):
                batch_success += 1
        
        end_time = time.perf_counter()
        batch_time = (end_time - start_time) * 1000
        
        batch_results.append({
            'batch_number': batch + 1,
            'messages_sent': batch_size,
            'successful': batch_success,
            'failed': batch_size - batch_success,
            'batch_time_ms': round(batch_time, 2),
            'throughput_msg_per_sec': round((batch_size / (batch_time / 1000)), 2) if batch_time > 0 else 0
        })
        
        time.sleep(0.5)
    
    total_messages = num_messages
    total_successful = sum([r['successful'] for r in batch_results])
    
    return {
        'test_type': 'mqtt_load_handling',
        'total_messages': total_messages,
        'total_successful': total_successful,
        'overall_success_rate': round((total_successful / total_messages) * 100, 2) if total_messages > 0 else 0,
        'average_throughput_msg_per_sec': round(stat_lib.mean([r['throughput_msg_per_sec'] for r in batch_results]), 2) if batch_results else 0,
        'batch_results': batch_results
    }


def test_broker_recovery(broker_down_time=5):
    """
    Test 5: Broker recovery after disconnection
    """
    # Connect and send a message
    client = mqtt.Client()
    client.connect(BROKER, PORT, 5)
    client.loop_start()
    time.sleep(0.5)
    
    test_packet = {
        "device_id": "RECOVERY_TEST",
        "device_type": "test",
        "timestamp": time.time(),
        "message": "Before disconnect"
    }
    send_packet(test_packet)
    
    # Disconnect
    client.disconnect()
    client.loop_stop()
    
    print(f"🔴 Broker disconnected. Waiting {broker_down_time} seconds...")
    time.sleep(broker_down_time)
    
    # Try to reconnect
    start_reconnect = time.time()
    reconnect_success = False
    
    for i in range(10):
        try:
            client = mqtt.Client()
            client.connect(BROKER, PORT, 5)
            reconnect_success = True
            break
        except:
            time.sleep(0.5)
    
    recovery_time = time.time() - start_reconnect if reconnect_success else 0
    
    return {
        'test_type': 'broker_recovery',
        'broker_down_duration_sec': broker_down_time,
        'recovered': reconnect_success,
        'recovery_time_sec': round(recovery_time, 2) if reconnect_success else None,
        'status': 'Recovered' if reconnect_success else 'Failed to recover'
    }


def test_message_integrity(num_tests=50):
    """
    Test 6: Message integrity during transmission
    """
    received_messages = []
    
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            received_messages.append(payload)
        except:
            pass
    
    # Setup subscriber
    sub_client = mqtt.Client()
    sub_client.on_message = on_message
    sub_client.connect(BROKER, PORT, 60)
    sub_client.subscribe(TOPIC)
    sub_client.loop_start()
    
    time.sleep(1)
    
    # Publish test messages with unique IDs
    pub_client = mqtt.Client()
    pub_client.connect(BROKER, PORT, 60)
    
    sent_messages = []
    for i in range(num_tests):
        message_content = f"Integrity test message {i} with unique content {i*12345}"
        test_packet = {
            "device_id": f"INTEGRITY_TEST_{i}",
            "device_type": "integrity_test",
            "message_id": i,
            "content": message_content,
            "timestamp": time.time(),
            "hash": str(hash(message_content))
        }
        sent_messages.append(test_packet)
        
        payload = json.dumps(test_packet)
        pub_client.publish(TOPIC, payload)
        time.sleep(0.1)
    
    time.sleep(3)
    
    sub_client.loop_stop()
    sub_client.disconnect()
    pub_client.disconnect()
    
    # Compare sent vs received
    corrupted = 0
    for sent in sent_messages:
        found = False
        for recv in received_messages:
            if recv.get('message_id') == sent.get('message_id'):
                found = True
                if recv.get('content') != sent.get('content'):
                    corrupted += 1
                break
        if not found:
            corrupted += 1
    
    integrity_rate = ((num_tests - corrupted) / num_tests) * 100 if num_tests > 0 else 0
    
    return {
        'test_type': 'message_integrity',
        'total_messages': num_tests,
        'messages_received': len(received_messages),
        'corrupted_messages': corrupted,
        'integrity_rate_percentage': round(integrity_rate, 2),
        'status': 'Excellent' if integrity_rate >= 99 else 'Good' if integrity_rate >= 95 else 'Poor'
    }


def get_mqtt_test_stats():
    """Get current MQTT test statistics"""
    return {
        'total_published': mqtt_test_stats['total_published'],
        'successful_publishes': mqtt_test_stats['successful_publishes'],
        'failed_publishes': mqtt_test_stats['failed_publishes'],
        'success_rate': round((mqtt_test_stats['successful_publishes'] / max(mqtt_test_stats['total_published'], 1)) * 100, 2),
        'connection_attempts': mqtt_test_stats['connection_attempts'],
        'successful_connections': mqtt_test_stats['successful_connections']
    }


def reset_mqtt_test_stats():
    """Reset all MQTT test statistics"""
    global mqtt_test_stats
    mqtt_test_stats = {
        'total_published': 0,
        'successful_publishes': 0,
        'failed_publishes': 0,
        'connection_attempts': 0,
        'successful_connections': 0
    }
    print("📊 MQTT test statistics reset")


def run_all_mqtt_tests():
    """
    Run all MQTT reliability tests
    """
    print("\n" + "="*60)
    print("🧪 Running MQTT Handler Reliability Tests")
    print("="*60)
    
    results = {
        'connection_reliability': test_mqtt_connection(15),
        'packet_publish_reliability': test_packet_publish_reliability(25),
        'mqtt_latency': test_mqtt_latency(30),
        'load_handling': test_mqtt_load_handling(50, 10),
        'message_integrity': test_message_integrity(30),
        'timestamp': time.time()
    }
    
    print("\n✅ All MQTT tests completed!")
    return results


# ========== MAIN FUNCTION ==========
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing MQTT Handler Module")
    print("="*60)
    
    # Test basic packet send
    print("\n📡 Testing basic packet send...")
    test_packet = {
        "device_id": "TEST_001",
        "device_type": "virtual",
        "timestamp": time.time()
    }
    
    result = send_packet(test_packet)
    print(f"Send result: {result}")
    
    # Run all reliability tests
    print("\n" + "="*60)
    print("Running MQTT Reliability Tests")
    print("="*60)
    
    results = run_all_mqtt_tests()
    
    # Print summary
    print("\n" + "="*60)
    print("📊 MQTT TEST SUMMARY")
    print("="*60)
    
    if 'connection_reliability' in results:
        cr = results['connection_reliability']
        print(f"\n✅ Connection Reliability: {cr['success_rate_percentage']}%")
        print(f"   Avg connection time: {cr['connection_times']['average_ms']} ms")
    
    if 'packet_publish_reliability' in results:
        pr = results['packet_publish_reliability']
        print(f"\n✅ Packet Publish Reliability: {pr['success_rate_percentage']}%")
        print(f"   Avg publish time: {pr['publish_times']['average_ms']} ms")
    
    if 'mqtt_latency' in results:
        lat = results['mqtt_latency']
        print(f"\n✅ MQTT Latency: {lat['latency']['average_ms']} ms avg")
        print(f"   Receive rate: {lat['receive_rate_percentage']}%")
    
    if 'load_handling' in results:
        lh = results['load_handling']
        print(f"\n✅ Load Handling: {lh['overall_success_rate']}% success")
        print(f"   Throughput: {lh['average_throughput_msg_per_sec']} msg/sec")
    
    if 'message_integrity' in results:
        mi = results['message_integrity']
        print(f"\n✅ Message Integrity: {mi['integrity_rate_percentage']}%")
        print(f"   Status: {mi['status']}")
    
    print("\n" + "="*60)