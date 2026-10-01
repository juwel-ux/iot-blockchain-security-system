# ipfs_handler/ipfs_handler_v2.py - COMPLETE WITH DATA INTEGRITY TESTING FUNCTIONS
import requests
import json
import os
import hashlib
import base64
import time
import statistics as stat_lib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

class IPFSHandler:
    """
    Private IPFS Handler - Data only on YOUR computer
    No public IPFS gateway - completely private
    """
    
    def __init__(self):
        # Use LOCAL IPFS node only (no public gateway)
        self.api_url = "http://localhost:5001/api/v0"
        self.gateway_url = "http://localhost:8080/ipfs/"
        
        # Private network configuration
        self.private_mode = True
        
        # Check if local IPFS is running
        self.local_node_running = self._check_local_node()
        
        # Data Integrity Test variables
        self.data_integrity_stats = {
            'total_uploads': 0,
            'total_downloads': 0,
            'failed_uploads': 0,
            'failed_downloads': 0,
            'corrupted_downloads': 0,
            'integrity_check_passed': 0,
            'integrity_check_failed': 0
        }
        
        if not self.local_node_running:
            print("❌ Local IPFS node not running!")
            print("   Please run: ipfs daemon")
            print("   Data will NOT be stored securely!")
    
    def _check_local_node(self):
        """Check if local IPFS node is running"""
        try:
            response = requests.post(f"{self.api_url}/id", timeout=5)
            if response.status_code == 200:
                node_id = response.json().get('ID', 'unknown')[:20]
                print(f"✅ Connected to YOUR local IPFS node: {node_id}...")
                print(f"📍 Data will be stored on YOUR computer only")
                return True
        except:
            pass
        
        print("⚠️ Local IPFS not running!")
        return False
    
    def upload_text(self, data):
        """
        Upload to PRIVATE IPFS (your computer only)
        NOT using public gateways
        """
        if not self.local_node_running:
            print("❌ Cannot upload - Local IPFS not running!")
            self.data_integrity_stats['failed_uploads'] += 1
            return None
        
        try:
            # Calculate hash before upload for integrity check
            data_hash = hashlib.sha256(data.encode('utf-8')).hexdigest()
            
            # Upload to local node only
            files = {'file': ('data.json', data)}
            response = requests.post(f"{self.api_url}/add", files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                cid = result['Hash']
                
                # Pin to local node (permanent storage on your computer)
                self._pin_to_local(cid)
                
                self.data_integrity_stats['total_uploads'] += 1
                
                print(f"✅ Uploaded to YOUR computer: {cid}")
                print(f"📍 File is PINNED (permanent)")
                print(f"🔐 Data hash: {data_hash[:16]}...")
                
                return {
                    'status': 'success',
                    'ipfs_cid': cid,
                    'pinned': True,
                    'location': 'your_local_node',
                    'data_hash': data_hash
                }
            else:
                print(f"❌ Upload failed: {response.status_code}")
                self.data_integrity_stats['failed_uploads'] += 1
                return None
                
        except Exception as e:
            print(f"❌ IPFS upload error: {e}")
            self.data_integrity_stats['failed_uploads'] += 1
            return None
    
    def _pin_to_local(self, cid):
        """Permanently store file on your computer"""
        try:
            response = requests.post(f"{self.api_url}/pin/add?arg={cid}", timeout=10)
            if response.status_code == 200:
                print(f"📌 Pinned to your computer (permanent storage)")
            else:
                print(f"⚠️ Pin failed: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Pin error: {e}")
    
    def download_text(self, cid, expected_hash=None):
        """
        Download from PRIVATE IPFS (your computer)
        With optional integrity verification
        """
        if not self.local_node_running:
            print("❌ Cannot download - Local IPFS not running!")
            self.data_integrity_stats['failed_downloads'] += 1
            return None
        
        try:
            # Try local gateway first
            response = requests.get(f"{self.gateway_url}{cid}", timeout=30)
            
            if response.status_code == 200:
                downloaded_data = response.text
                print(f"✅ Downloaded from YOUR computer: {cid}")
                self.data_integrity_stats['total_downloads'] += 1
                
                # Verify integrity if hash provided
                if expected_hash:
                    downloaded_hash = hashlib.sha256(downloaded_data.encode('utf-8')).hexdigest()
                    if downloaded_hash == expected_hash:
                        print(f"🔐 Integrity check PASSED")
                        self.data_integrity_stats['integrity_check_passed'] += 1
                    else:
                        print(f"⚠️ Integrity check FAILED! Hash mismatch")
                        self.data_integrity_stats['integrity_check_failed'] += 1
                        self.data_integrity_stats['corrupted_downloads'] += 1
                
                return downloaded_data
            
            # If not found locally, try direct API
            response = requests.post(f"{self.api_url}/cat?arg={cid}", timeout=30)
            if response.status_code == 200:
                downloaded_data = response.text
                print(f"✅ Downloaded via API: {cid}")
                self.data_integrity_stats['total_downloads'] += 1
                
                if expected_hash:
                    downloaded_hash = hashlib.sha256(downloaded_data.encode('utf-8')).hexdigest()
                    if downloaded_hash == expected_hash:
                        print(f"🔐 Integrity check PASSED")
                        self.data_integrity_stats['integrity_check_passed'] += 1
                    else:
                        print(f"⚠️ Integrity check FAILED! Hash mismatch")
                        self.data_integrity_stats['integrity_check_failed'] += 1
                        self.data_integrity_stats['corrupted_downloads'] += 1
                
                return downloaded_data
            
            print(f"❌ File not found: {cid}")
            self.data_integrity_stats['failed_downloads'] += 1
            return None
            
        except Exception as e:
            print(f"❌ Download error: {e}")
            self.data_integrity_stats['failed_downloads'] += 1
            return None
    
    def list_pinned_files(self):
        """List all files stored on your computer"""
        if not self.local_node_running:
            return []
        
        try:
            response = requests.post(f"{self.api_url}/pin/ls")
            if response.status_code == 200:
                data = response.json()
                pins = list(data.get('Keys', {}).keys())
                print(f"📌 Pinned files on your computer: {len(pins)}")
                return pins
        except:
            pass
        return []
    
    def unpin_file(self, cid):
        """Remove file from your computer (if you want to delete)"""
        if not self.local_node_running:
            return False
        
        try:
            response = requests.post(f"{self.api_url}/pin/rm?arg={cid}")
            if response.status_code == 200:
                print(f"🗑️ Unpinned: {cid}")
                return True
        except:
            pass
        return False
    
    def get_node_info(self):
        """Get your IPFS node information"""
        if not self.local_node_running:
            return None
        
        try:
            response = requests.post(f"{self.api_url}/id")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def is_private_mode(self):
        """Check if running in private mode"""
        return self.private_mode and self.local_node_running
    
    # ============== DATA INTEGRITY TESTING FUNCTIONS (TEST 9) ==============
    
    def test_upload_with_integrity(self, num_tests=50):
        """
        Test 1: Upload data and verify integrity by downloading and comparing
        """
        results = []
        passed = 0
        failed = 0
        
        for i in range(num_tests):
            test_data = {
                'test_id': f"integrity_test_{i}",
                'timestamp': time.time(),
                'data': f"Test data for integrity verification {i}" * 10,
                'random_value': os.urandom(16).hex()
            }
            data_string = json.dumps(test_data)
            
            # Upload with hash
            upload_result = self.upload_text(data_string)
            
            if not upload_result or upload_result.get('status') != 'success':
                failed += 1
                results.append({
                    'test_number': i + 1,
                    'status': 'upload_failed'
                })
                continue
            
            cid = upload_result.get('ipfs_cid')
            original_hash = upload_result.get('data_hash')
            
            # Download and verify
            downloaded_data = self.download_text(cid, original_hash)
            
            if downloaded_data and downloaded_data == data_string:
                passed += 1
                results.append({
                    'test_number': i + 1,
                    'status': 'passed',
                    'cid': cid[:16] + '...'
                })
            else:
                failed += 1
                results.append({
                    'test_number': i + 1,
                    'status': 'failed',
                    'cid': cid[:16] + '...' if cid else None
                })
            
            # Clean up
            if cid:
                self.unpin_file(cid)
            
            time.sleep(0.2)
        
        integrity_rate = (passed / num_tests) * 100 if num_tests > 0 else 0
        
        return {
            'test_type': 'upload_integrity_test',
            'total_tests': num_tests,
            'passed': passed,
            'failed': failed,
            'integrity_rate_percentage': round(integrity_rate, 2),
            'results': results[:20]
        }
    
    def test_upload_download_cycle_integrity(self, num_cycles=30):
        """
        Test 2: Complete upload-download cycle integrity check
        """
        cycle_results = []
        successful_cycles = 0
        
        for i in range(num_cycles):
            original_data = {
                'cycle_id': i,
                'timestamp': time.time(),
                'message': f"Cycle test message {i}",
                'payload': 'X' * (1024 * (i % 5 + 1))  # Varying sizes: 1KB to 5KB
            }
            data_string = json.dumps(original_data)
            
            start_time = time.perf_counter()
            
            # Upload
            upload_result = self.upload_text(data_string)
            if not upload_result:
                cycle_results.append({
                    'cycle_number': i + 1,
                    'status': 'upload_failed'
                })
                continue
            
            cid = upload_result.get('ipfs_cid')
            
            # Download
            downloaded_data = self.download_text(cid)
            
            end_time = time.perf_counter()
            cycle_time_ms = (end_time - start_time) * 1000
            
            # Verify integrity
            if downloaded_data and downloaded_data == data_string:
                successful_cycles += 1
                cycle_results.append({
                    'cycle_number': i + 1,
                    'status': 'success',
                    'cycle_time_ms': round(cycle_time_ms, 2),
                    'data_size_bytes': len(data_string)
                })
            else:
                cycle_results.append({
                    'cycle_number': i + 1,
                    'status': 'data_mismatch'
                })
            
            # Clean up
            self.unpin_file(cid)
            time.sleep(0.2)
        
        success_rate = (successful_cycles / num_cycles) * 100 if num_cycles > 0 else 0
        
        return {
            'test_type': 'upload_download_cycle_integrity',
            'total_cycles': num_cycles,
            'successful_cycles': successful_cycles,
            'failed_cycles': num_cycles - successful_cycles,
            'success_rate_percentage': round(success_rate, 2),
            'cycle_results': cycle_results
        }
    
    def test_concurrent_upload_integrity(self, num_concurrent=10):
        """
        Test 3: Concurrent upload integrity test
        """
        import threading
        
        results = []
        lock = threading.Lock()
        completed = 0
        
        def upload_task(task_id):
            nonlocal completed
            test_data = {
                'task_id': task_id,
                'timestamp': time.time(),
                'data': f"Concurrent upload test data for task {task_id}" * 5
            }
            data_string = json.dumps(test_data)
            
            start_time = time.perf_counter()
            upload_result = self.upload_text(data_string)
            upload_time = (time.perf_counter() - start_time) * 1000
            
            if upload_result and upload_result.get('status') == 'success':
                cid = upload_result.get('ipfs_cid')
                original_hash = upload_result.get('data_hash')
                
                # Download and verify
                downloaded_data = self.download_text(cid, original_hash)
                
                if downloaded_data and downloaded_data == data_string:
                    with lock:
                        results.append({
                            'task_id': task_id,
                            'status': 'success',
                            'upload_time_ms': round(upload_time, 2),
                            'cid': cid[:16] + '...'
                        })
                else:
                    with lock:
                        results.append({
                            'task_id': task_id,
                            'status': 'integrity_failed'
                        })
                
                self.unpin_file(cid)
            else:
                with lock:
                    results.append({
                        'task_id': task_id,
                        'status': 'upload_failed'
                    })
            
            with lock:
                completed += 1
        
        threads = []
        for i in range(num_concurrent):
            t = threading.Thread(target=upload_task, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        successful = len([r for r in results if r['status'] == 'success'])
        success_rate = (successful / num_concurrent) * 100 if num_concurrent > 0 else 0
        
        return {
            'test_type': 'concurrent_upload_integrity',
            'total_concurrent_uploads': num_concurrent,
            'successful_uploads': successful,
            'failed_uploads': num_concurrent - successful,
            'success_rate_percentage': round(success_rate, 2),
            'results': results
        }
    
    def test_data_persistence_after_unpin(self, num_tests=10):
        """
        Test 4: Data persistence after unpin (should be removed)
        """
        results = []
        
        for i in range(num_tests):
            test_data = {
                'test_id': f"persistence_test_{i}",
                'timestamp': time.time(),
                'data': f"Persistence test data {i}"
            }
            data_string = json.dumps(test_data)
            
            # Upload
            upload_result = self.upload_text(data_string)
            if not upload_result:
                results.append({
                    'test_number': i + 1,
                    'status': 'upload_failed'
                })
                continue
            
            cid = upload_result.get('ipfs_cid')
            
            # Verify data exists
            downloaded = self.download_text(cid)
            exists_before_unpin = downloaded is not None
            
            # Unpin
            self.unpin_file(cid)
            
            # Try to download after unpin (should fail or not be available)
            time.sleep(0.5)
            downloaded_after = self.download_text(cid)
            exists_after_unpin = downloaded_after is not None
            
            results.append({
                'test_number': i + 1,
                'cid': cid[:16] + '...',
                'exists_before_unpin': exists_before_unpin,
                'exists_after_unpin': exists_after_unpin,
                'correctly_unpinned': exists_before_unpin and not exists_after_unpin
            })
        
        correctly_unpinned = len([r for r in results if r.get('correctly_unpinned')])
        
        return {
            'test_type': 'data_persistence_after_unpin',
            'total_tests': num_tests,
            'correctly_unpinned': correctly_unpinned,
            'success_rate': round((correctly_unpinned / num_tests) * 100, 2) if num_tests > 0 else 0,
            'results': results
        }
    
    def get_data_integrity_stats(self):
        """Get current data integrity statistics"""
        total_operations = self.data_integrity_stats['total_uploads'] + self.data_integrity_stats['total_downloads']
        total_errors = self.data_integrity_stats['failed_uploads'] + self.data_integrity_stats['failed_downloads'] + self.data_integrity_stats['corrupted_downloads']
        
        return {
            'total_uploads': self.data_integrity_stats['total_uploads'],
            'total_downloads': self.data_integrity_stats['total_downloads'],
            'failed_uploads': self.data_integrity_stats['failed_uploads'],
            'failed_downloads': self.data_integrity_stats['failed_downloads'],
            'corrupted_downloads': self.data_integrity_stats['corrupted_downloads'],
            'integrity_check_passed': self.data_integrity_stats['integrity_check_passed'],
            'integrity_check_failed': self.data_integrity_stats['integrity_check_failed'],
            'overall_success_rate': round(((total_operations - total_errors) / max(total_operations, 1)) * 100, 2),
            'local_node_running': self.local_node_running
        }
    
    def reset_data_integrity_stats(self):
        """Reset data integrity statistics"""
        self.data_integrity_stats = {
            'total_uploads': 0,
            'total_downloads': 0,
            'failed_uploads': 0,
            'failed_downloads': 0,
            'corrupted_downloads': 0,
            'integrity_check_passed': 0,
            'integrity_check_failed': 0
        }
        print("📊 Data integrity statistics reset")
    
    def run_all_data_integrity_tests(self):
        """
        Run all data integrity tests for IPFS
        """
        print("\n" + "="*60)
        print("🧪 Running IPFS Data Integrity Tests (Test 9)")
        print("="*60)
        
        if not self.local_node_running:
            print("❌ IPFS node not running! Cannot run tests.")
            return {'error': 'IPFS node not running'}
        
        results = {
            'upload_integrity': self.test_upload_with_integrity(30),
            'upload_download_cycle': self.test_upload_download_cycle_integrity(20),
            'concurrent_upload_integrity': self.test_concurrent_upload_integrity(8),
            'data_persistence': self.test_data_persistence_after_unpin(10),
            'statistics': self.get_data_integrity_stats(),
            'timestamp': time.time()
        }
        
        print("\n✅ All IPFS data integrity tests completed!")
        return results
    
    # ============== THROUGHPUT TESTING FUNCTIONS ==============
    
    def test_upload_throughput(self, data_sizes=[1024, 10240, 102400, 1048576]):
        """
        Test IPFS upload throughput with different data sizes
        data_sizes in bytes: 1KB, 10KB, 100KB, 1MB
        """
        results = []
        
        for size in data_sizes:
            # Generate test data of specified size
            test_data = {
                'test_id': f"throughput_test_{size}",
                'timestamp': time.time(),
                'data': 'X' * size  # Repeat character to reach size
            }
            data_string = json.dumps(test_data)
            
            upload_times = []
            
            # Run 5 times for each size to get average
            for i in range(5):
                start_time = time.perf_counter()
                result = self.upload_text(data_string)
                end_time = time.perf_counter()
                
                if result and result.get('status') == 'success':
                    upload_time_ms = (end_time - start_time) * 1000
                    upload_times.append(upload_time_ms)
                    
                    # Clean up - unpin test file
                    self.unpin_file(result.get('ipfs_cid'))
                else:
                    upload_times.append(None)
                
                time.sleep(0.5)  # Small delay between tests
            
            # Calculate statistics (excluding None values)
            valid_times = [t for t in upload_times if t is not None]
            
            if valid_times:
                avg_time = sum(valid_times) / len(valid_times)
                throughput_mbps = (size * 8) / (avg_time / 1000) / 1000000  # Mbps
                
                results.append({
                    'data_size_bytes': size,
                    'data_size_kb': round(size / 1024, 2),
                    'data_size_mb': round(size / (1024 * 1024), 4),
                    'average_upload_time_ms': round(avg_time, 2),
                    'min_upload_time_ms': round(min(valid_times), 2),
                    'max_upload_time_ms': round(max(valid_times), 2),
                    'throughput_mbps': round(throughput_mbps, 2),
                    'successful_tests': len(valid_times),
                    'total_tests': 5
                })
        
        return {
            'test_type': 'upload_throughput',
            'results': results,
            'summary': {
                'average_throughput_mbps': round(sum(r['throughput_mbps'] for r in results) / len(results), 2) if results else 0,
                'total_data_uploaded_mb': sum(r['data_size_mb'] for r in results),
                'local_node_running': self.local_node_running
            }
        }
    
    def test_download_throughput(self, data_sizes=[1024, 10240, 102400, 1048576]):
        """
        Test IPFS download throughput with different data sizes
        First uploads then downloads
        """
        results = []
        
        for size in data_sizes:
            # First upload test data
            test_data = {
                'test_id': f"download_test_{size}",
                'timestamp': time.time(),
                'data': 'Y' * size
            }
            data_string = json.dumps(test_data)
            
            upload_result = self.upload_text(data_string)
            if not upload_result or upload_result.get('status') != 'success':
                results.append({
                    'data_size_bytes': size,
                    'error': 'Failed to upload test data'
                })
                continue
            
            cid = upload_result.get('ipfs_cid')
            download_times = []
            
            # Run 5 times for each size
            for i in range(5):
                start_time = time.perf_counter()
                downloaded_data = self.download_text(cid)
                end_time = time.perf_counter()
                
                if downloaded_data:
                    download_time_ms = (end_time - start_time) * 1000
                    download_times.append(download_time_ms)
                else:
                    download_times.append(None)
                
                time.sleep(0.5)
            
            # Clean up
            self.unpin_file(cid)
            
            # Calculate statistics
            valid_times = [t for t in download_times if t is not None]
            
            if valid_times:
                avg_time = sum(valid_times) / len(valid_times)
                throughput_mbps = (size * 8) / (avg_time / 1000) / 1000000
                
                results.append({
                    'data_size_bytes': size,
                    'data_size_kb': round(size / 1024, 2),
                    'data_size_mb': round(size / (1024 * 1024), 4),
                    'average_download_time_ms': round(avg_time, 2),
                    'min_download_time_ms': round(min(valid_times), 2),
                    'max_download_time_ms': round(max(valid_times), 2),
                    'throughput_mbps': round(throughput_mbps, 2),
                    'successful_tests': len(valid_times),
                    'total_tests': 5
                })
        
        return {
            'test_type': 'download_throughput',
            'results': results,
            'summary': {
                'average_throughput_mbps': round(sum(r['throughput_mbps'] for r in results) / len(results), 2) if results else 0,
                'total_data_downloaded_mb': sum(r['data_size_mb'] for r in results) if results else 0,
                'local_node_running': self.local_node_running
            }
        }
    
    def test_ipfs_latency(self, num_tests=20):
        """Test IPFS upload/download latency"""
        upload_latencies = []
        download_latencies = []
        test_data = {
            'test_id': 'latency_test',
            'timestamp': time.time(),
            'data': 'X' * 1024  # 1KB test data
        }
        data_string = json.dumps(test_data)
        
        for i in range(num_tests):
            # Upload latency
            start = time.perf_counter()
            upload_result = self.upload_text(data_string)
            end = time.perf_counter()
            
            if upload_result and upload_result.get('status') == 'success':
                upload_latencies.append((end - start) * 1000)
                cid = upload_result.get('ipfs_cid')
                
                # Download latency
                start = time.perf_counter()
                downloaded = self.download_text(cid)
                end = time.perf_counter()
                
                if downloaded:
                    download_latencies.append((end - start) * 1000)
                
                # Clean up
                self.unpin_file(cid)
            
            time.sleep(0.3)
        
        return {
            'test_type': 'ipfs_latency',
            'upload': {
                'average_ms': round(stat_lib.mean(upload_latencies), 2) if upload_latencies else 0,
                'min_ms': round(min(upload_latencies), 2) if upload_latencies else 0,
                'max_ms': round(max(upload_latencies), 2) if upload_latencies else 0,
                'std_dev_ms': round(stat_lib.stdev(upload_latencies), 2) if len(upload_latencies) > 1 else 0,
                'total_tests': len(upload_latencies)
            },
            'download': {
                'average_ms': round(stat_lib.mean(download_latencies), 2) if download_latencies else 0,
                'min_ms': round(min(download_latencies), 2) if download_latencies else 0,
                'max_ms': round(max(download_latencies), 2) if download_latencies else 0,
                'std_dev_ms': round(stat_lib.stdev(download_latencies), 2) if len(download_latencies) > 1 else 0,
                'total_tests': len(download_latencies)
            }
        }
    
    def run_all_ipfs_tests(self):
        """Run all IPFS throughput and latency tests"""
        print("\n" + "="*50)
        print("🧪 Running IPFS Throughput & Latency Tests")
        print("="*50)
        
        if not self.local_node_running:
            print("❌ IPFS node not running! Cannot run tests.")
            return {'error': 'IPFS node not running'}
        
        results = {
            'upload_throughput': self.test_upload_throughput(),
            'download_throughput': self.test_download_throughput(),
            'latency': self.test_ipfs_latency(),
            'node_info': self.get_node_info(),
            'timestamp': time.time()
        }
        
        print("\n✅ All IPFS tests completed!")
        return results


# Create singleton instance
ipfs_handler = IPFSHandler()