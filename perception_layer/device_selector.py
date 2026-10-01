# perception_layer/device_selector.py
import uuid
import serial
import serial.tools.list_ports
import json
import time
import statistics as stat_lib

# Relative imports (current package)
from .db_handler import add_device
from .data_generator import generate_secret_key

# Serial import for Arduino
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("pyserial not installed. Real Arduino device will not work.")
    print("Install with: pip install pyserial")


def get_available_ports():
    """Get list of available serial ports"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


def detect_arduino():
    """Detect Arduino device and get its ID"""
    try:
        ports = get_available_ports()
        for port in ports:
            try:
                ser = serial.Serial(port, 9600, timeout=2)
                time.sleep(2)  # Wait for Arduino to initialize
                
                # Send command to get device ID
                ser.write(b"GET_ID\n")
                time.sleep(1)
                
                if ser.in_waiting:
                    line = ser.readline().decode().strip()
                    ser.close()
                    
                    # Try to parse JSON
                    try:
                        data = json.loads(line)
                        if 'device_id' in data:
                            return data['device_id'], data.get('device_type', 'real'), line
                    except:
                        # If not JSON, try to extract from text
                        if "Device ID:" in line:
                            device_id = line.split(":")[1].strip()
                            return device_id, 'real', line
                
                ser.close()
            except Exception as e:
                print(f"Error reading from {port}: {e}")
                continue
        
        return None, None, None
    except Exception as e:
        print(f"Error detecting Arduino: {e}")
        return None, None, None


def generate_device_id(device_type, arduino_port=None):
    """
    Generate Device ID:
    - Virtual: UUID
    - Real: Read from Arduino or generate fallback
    """
    if device_type == "virtual":
        return "VDEV_" + str(uuid.uuid4())
    else:
        # Real Arduino device
        if not SERIAL_AVAILABLE:
            return "REALDEV_" + str(uuid.uuid4().hex[:12].upper())
        
        try:
            if arduino_port:
                ser = serial.Serial(arduino_port, 9600, timeout=2)
            else:
                # Auto-detect Arduino
                ports = get_available_ports()
                if not ports:
                    print("No serial ports found")
                    return "REALDEV_" + str(uuid.uuid4().hex[:12].upper())
                
                ser = serial.Serial(ports[0], 9600, timeout=2)
            
            time.sleep(2)  # Wait for Arduino to reset
            
            # Send command to get device ID
            ser.write(b"GET_ID\n")
            time.sleep(1)
            
            if ser.in_waiting:
                line = ser.readline().decode().strip()
                ser.close()
                
                # Try to parse JSON
                try:
                    data = json.loads(line)
                    if 'device_id' in data:
                        return data['device_id']
                except:
                    # If not JSON, try to extract
                    if "Device ID:" in line:
                        device_id = line.split(":")[1].strip()
                        return device_id
                    else:
                        return line
            else:
                ser.close()
                return "REALDEV_" + str(uuid.uuid4().hex[:12].upper())
                
        except Exception as e:
            print(f"Arduino connection error: {e}")
            return "REALDEV_" + str(uuid.uuid4().hex[:12].upper())


def register_device(device_type="virtual", arduino_port=None):
    """
    Register device step-by-step and return outputs for display
    """
    output_steps = []

    # Step 1: Generate/Read Device ID
    device_id = generate_device_id(device_type, arduino_port)
    output_steps.append(f"{device_type.capitalize()} device is created.")
    output_steps.append(f"Device ID: {device_id}")
    
    if device_type == "real":
        output_steps.append("🔌 Arduino device detected and connected")
        output_steps.append(f"📡 Serial Port: {arduino_port if arduino_port else 'Auto-detected'}")

    # Step 2: Save to database
    add_device(device_id, device_type, "SECRET_HASH_HIDDEN")
    output_steps.append("✅ This ID is saved in MongoDB")

    # Step 3: Generate secret key
    secret_key, secret_hash = generate_secret_key()
    output_steps.append(f"🔐 Secret key created: {secret_key[:16]}...")
    output_steps.append("✅ Secret key hashed and stored securely")

    return output_steps


# ============== DEVICE REGISTRATION TESTING FUNCTIONS ==============

def test_device_registration_time(device_type="virtual", num_tests=20):
    """
    Test 1: Measure device registration time
    Returns average registration time in seconds
    """
    registration_times = []
    results = []
    
    for i in range(num_tests):
        start_time = time.perf_counter()
        outputs = register_device(device_type, None)
        end_time = time.perf_counter()
        
        registration_time = (end_time - start_time) * 1000  # Convert to ms
        registration_times.append(registration_time)
        
        # Extract device ID from outputs
        device_id = None
        for line in outputs:
            if "Device ID:" in line:
                device_id = line.split(":")[1].strip()
                break
        
        results.append({
            'test_number': i + 1,
            'registration_time_ms': round(registration_time, 2),
            'device_id': device_id
        })
        
        time.sleep(0.1)  # Small delay between tests
    
    return {
        'test_type': 'device_registration_time',
        'device_type': device_type,
        'total_tests': num_tests,
        'registration_times_ms': results,
        'statistics': {
            'average_ms': round(stat_lib.mean(registration_times), 2),
            'min_ms': round(min(registration_times), 2),
            'max_ms': round(max(registration_times), 2),
            'std_dev_ms': round(stat_lib.stdev(registration_times), 2) if len(registration_times) > 1 else 0
        }
    }


def test_virtual_device_bulk_registration(num_devices=50):
    """
    Test 2: Bulk registration of virtual devices
    Tests scalability and throughput of device registration
    """
    results = []
    start_total = time.time()
    
    for i in range(num_devices):
        start_time = time.perf_counter()
        outputs = register_device("virtual", None)
        end_time = time.perf_counter()
        
        registration_time_ms = (end_time - start_time) * 1000
        
        # Extract device ID
        device_id = None
        for line in outputs:
            if "Device ID:" in line:
                device_id = line.split(":")[1].strip()
                break
        
        results.append({
            'device_number': i + 1,
            'device_id': device_id,
            'registration_time_ms': round(registration_time_ms, 2)
        })
        
        if (i + 1) % 10 == 0:
            print(f"   Registered {i + 1}/{num_devices} devices...")
    
    end_total = time.time()
    total_time_ms = (end_total - start_total) * 1000
    
    registration_times = [r['registration_time_ms'] for r in results]
    
    return {
        'test_type': 'bulk_registration',
        'total_devices': num_devices,
        'total_time_ms': round(total_time_ms, 2),
        'average_per_device_ms': round(stat_lib.mean(registration_times), 2),
        'throughput_devices_per_second': round(num_devices / (total_time_ms / 1000), 2),
        'statistics': {
            'min_ms': round(min(registration_times), 2),
            'max_ms': round(max(registration_times), 2),
            'std_dev_ms': round(stat_lib.stdev(registration_times), 2) if len(registration_times) > 1 else 0
        },
        'individual_results': results[:10]  # First 10 results only
    }


def test_real_device_detection(num_tests=10):
    """
    Test 3: Real Arduino device detection time
    """
    if not SERIAL_AVAILABLE:
        return {'error': 'pyserial not installed', 'serial_available': False}
    
    detection_times = []
    success_count = 0
    
    for i in range(num_tests):
        start_time = time.perf_counter()
        device_id, device_type, response = detect_arduino()
        end_time = time.perf_counter()
        
        detection_time_ms = (end_time - start_time) * 1000
        detection_times.append(detection_time_ms)
        
        if device_id:
            success_count += 1
        
        time.sleep(0.5)
    
    return {
        'test_type': 'real_device_detection',
        'total_tests': num_tests,
        'successful_detections': success_count,
        'detection_rate_percentage': round((success_count / num_tests) * 100, 2),
        'detection_times_ms': detection_times,
        'statistics': {
            'average_ms': round(stat_lib.mean(detection_times), 2) if detection_times else 0,
            'min_ms': round(min(detection_times), 2) if detection_times else 0,
            'max_ms': round(max(detection_times), 2) if detection_times else 0
        },
        'serial_available': SERIAL_AVAILABLE
    }


def test_serial_port_discovery():
    """
    Test 4: Serial port discovery time and available ports
    """
    start_time = time.perf_counter()
    ports = get_available_ports()
    end_time = time.perf_counter()
    
    discovery_time_ms = (end_time - start_time) * 1000
    
    return {
        'test_type': 'serial_port_discovery',
        'discovery_time_ms': round(discovery_time_ms, 2),
        'available_ports': ports,
        'port_count': len(ports),
        'serial_available': SERIAL_AVAILABLE
    }


def test_device_id_generation(device_type="virtual", num_tests=100):
    """
    Test 5: Device ID generation uniqueness and time
    """
    generated_ids = []
    generation_times = []
    
    for i in range(num_tests):
        start_time = time.perf_counter()
        device_id = generate_device_id(device_type, None)
        end_time = time.perf_counter()
        
        generation_time_ms = (end_time - start_time) * 1000
        generation_times.append(generation_time_ms)
        generated_ids.append(device_id)
    
    # Check uniqueness
    unique_ids = set(generated_ids)
    duplicate_count = num_tests - len(unique_ids)
    
    return {
        'test_type': 'device_id_generation',
        'device_type': device_type,
        'total_generated': num_tests,
        'unique_ids': len(unique_ids),
        'duplicate_count': duplicate_count,
        'uniqueness_rate': round((len(unique_ids) / num_tests) * 100, 2),
        'generation_times_ms': {
            'average_ms': round(stat_lib.mean(generation_times), 3),
            'min_ms': round(min(generation_times), 3),
            'max_ms': round(max(generation_times), 3)
        },
        'sample_ids': generated_ids[:5]
    }


def test_concurrent_registration(num_concurrent=10):
    """
    Test 6: Concurrent device registration using threading
    """
    import threading
    
    results = []
    lock = threading.Lock()
    
    def register_concurrent(thread_id):
        start_time = time.perf_counter()
        outputs = register_device("virtual", None)
        end_time = time.perf_counter()
        
        registration_time_ms = (end_time - start_time) * 1000
        
        device_id = None
        for line in outputs:
            if "Device ID:" in line:
                device_id = line.split(":")[1].strip()
                break
        
        with lock:
            results.append({
                'thread_id': thread_id,
                'device_id': device_id,
                'registration_time_ms': round(registration_time_ms, 2)
            })
    
    threads = []
    start_total = time.time()
    
    for i in range(num_concurrent):
        t = threading.Thread(target=register_concurrent, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    end_total = time.time()
    total_time_ms = (end_total - start_total) * 1000
    
    registration_times = [r['registration_time_ms'] for r in results]
    
    return {
        'test_type': 'concurrent_registration',
        'concurrent_devices': num_concurrent,
        'total_time_ms': round(total_time_ms, 2),
        'average_per_device_ms': round(stat_lib.mean(registration_times), 2),
        'throughput_devices_per_second': round(num_concurrent / (total_time_ms / 1000), 2),
        'successful_registrations': len(results),
        'statistics': {
            'min_ms': round(min(registration_times), 2),
            'max_ms': round(max(registration_times), 2)
        }
    }


def run_all_device_tests():
    """
    Run all device registration and detection tests
    """
    print("\n" + "="*60)
    print("🧪 Running Device Registration & Detection Tests")
    print("="*60)
    
    results = {
        'virtual_device_registration_time': test_device_registration_time("virtual", 20),
        'bulk_registration': test_virtual_device_bulk_registration(30),
        'device_id_uniqueness': test_device_id_generation("virtual", 50),
        'concurrent_registration': test_concurrent_registration(10),
        'serial_port_discovery': test_serial_port_discovery(),
        'real_device_detection': test_real_device_detection(5),
        'timestamp': time.time()
    }
    
    print("\n✅ All device tests completed!")
    return results


def get_device_test_metrics():
    """
    Get all device test metrics summary
    """
    virtual_test = test_device_registration_time("virtual", 10)
    bulk_test = test_virtual_device_bulk_registration(20)
    uniqueness_test = test_device_id_generation("virtual", 30)
    
    return {
        'virtual_device_avg_registration_ms': virtual_test['statistics']['average_ms'],
        'bulk_registration_throughput': bulk_test['throughput_devices_per_second'],
        'device_id_uniqueness_rate': uniqueness_test['uniqueness_rate'],
        'serial_available': SERIAL_AVAILABLE,
        'last_test_time': time.time()
    }


# ----------------------------
# CLI Run (optional)
# ----------------------------
if __name__ == "__main__":
    import time
    print("Select device type:")
    print("1. Virtual Device")
    print("2. Real Arduino Device")
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        print("\n🔍 Detecting Arduino devices...")
        ports = get_available_ports()
        if ports:
            print(f"Available ports: {ports}")
            port = input(f"Select port (default: {ports[0]}): ").strip()
            if not port:
                port = ports[0]
            device_type = "real"
            arduino_port = port
        else:
            print("No Arduino devices found. Using virtual mode.")
            device_type = "virtual"
            arduino_port = None
    else:
        device_type = "virtual"
        arduino_port = None
    
    outputs = register_device(device_type, arduino_port)
    print("\n--- Device Registration Steps ---")
    for line in outputs:
        print(line)
    
    # Ask if user wants to run tests
    print("\n" + "-"*40)
    run_tests = input("Run device tests? (y/n): ").strip().lower()
    if run_tests == 'y':
        results = run_all_device_tests()
        print("\n📊 Test Results:")
        print(json.dumps(results, indent=2, default=str))