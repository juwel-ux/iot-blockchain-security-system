# web_app/ipfs_handler_v2.py
import requests
import json
import hashlib
import os
import base64

class IPFSHandler:
    """Complete IPFS Handler for Decentralized File Storage"""
    
    def __init__(self, api_url="http://127.0.0.1:5001"):
        self.api_url = api_url
        self.gateway_url = "http://127.0.0.1:8080"
    
    def test_connection(self):
        """Test IPFS connection"""
        try:
            response = requests.post(f"{self.api_url}/api/v0/version", timeout=5)
            if response.status_code == 200:
                version = response.json()
                print(f"✅ IPFS Connected! Version: {version.get('Version')}")
                return True
        except Exception as e:
            print(f"❌ IPFS Connection failed: {e}")
        return False
    
    def upload_text(self, text):
        """
        Upload text to IPFS
        Returns: dict with ipfs_cid, data_hash, size
        """
        try:
            files = {'file': ('message.txt', text.encode('utf-8'))}
            response = requests.post(f"{self.api_url}/api/v0/add", files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                ipfs_cid = result['Hash']
                data_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                
                print(f"📤 Uploaded to IPFS:")
                print(f"   CID: {ipfs_cid}")
                print(f"   Hash: {data_hash[:32]}...")
                print(f"   Size: {len(text)} bytes")
                
                return {
                    'ipfs_cid': ipfs_cid,
                    'data_hash': data_hash,
                    'size': len(text)
                }
        except Exception as e:
            print(f"❌ IPFS upload failed: {e}")
        return None
    
    def upload_file(self, file_path):
        """
        Upload file to IPFS
        Returns: dict with ipfs_cid, data_hash, size, filename
        """
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                files = {'file': (os.path.basename(file_path), file_data)}
                response = requests.post(f"{self.api_url}/api/v0/add", files=files, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    ipfs_cid = result['Hash']
                    data_hash = hashlib.sha256(file_data).hexdigest()
                    
                    print(f"📤 Uploaded file to IPFS:")
                    print(f"   File: {file_path}")
                    print(f"   CID: {ipfs_cid}")
                    print(f"   Hash: {data_hash[:32]}...")
                    print(f"   Size: {len(file_data)} bytes")
                    
                    return {
                        'ipfs_cid': ipfs_cid,
                        'data_hash': data_hash,
                        'size': len(file_data),
                        'filename': os.path.basename(file_path)
                    }
        except Exception as e:
            print(f"❌ File upload failed: {e}")
        return None
    
    def upload_bytes(self, data, filename="file.bin"):
        """
        Upload bytes data to IPFS
        Returns: dict with ipfs_cid, data_hash, size
        """
        try:
            files = {'file': (filename, data)}
            response = requests.post(f"{self.api_url}/api/v0/add", files=files, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                ipfs_cid = result['Hash']
                data_hash = hashlib.sha256(data).hexdigest()
                
                return {
                    'ipfs_cid': ipfs_cid,
                    'data_hash': data_hash,
                    'size': len(data)
                }
        except Exception as e:
            print(f"❌ Bytes upload failed: {e}")
        return None
    
    def download_text(self, ipfs_cid):
        """
        Download text from IPFS by CID
        Returns: text content or None
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/v0/cat",
                params={'arg': ipfs_cid},
                timeout=30
            )
            if response.status_code == 200:
                text = response.text
                print(f"📥 Downloaded from IPFS: {ipfs_cid}")
                print(f"   Size: {len(text)} bytes")
                return text
        except Exception as e:
            print(f"❌ Download failed: {e}")
        return None
    
    def download_file(self, ipfs_cid, output_path):
        """
        Download file from IPFS by CID and save to output_path
        Returns: True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/v0/cat",
                params={'arg': ipfs_cid},
                timeout=60
            )
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"📥 Downloaded file to: {output_path}")
                print(f"   Size: {len(response.content)} bytes")
                return True
        except Exception as e:
            print(f"❌ File download failed: {e}")
        return False
    
    def pin_file(self, ipfs_cid):
        """Pin file to local IPFS node (prevents garbage collection)"""
        try:
            response = requests.post(
                f"{self.api_url}/api/v0/pin/add",
                params={'arg': ipfs_cid},
                timeout=30
            )
            if response.status_code == 200:
                print(f"📌 Pinned: {ipfs_cid}")
                return True
        except Exception as e:
            print(f"❌ Pin failed: {e}")
        return False
    
    def get_file_info(self, ipfs_cid):
        """Get file information from IPFS"""
        try:
            response = requests.post(
                f"{self.api_url}/api/v0/object/stat",
                params={'arg': ipfs_cid},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"❌ Get info failed: {e}")
        return None
    
    def list_local_files(self):
        """List local IPFS files"""
        try:
            response = requests.post(f"{self.api_url}/api/v0/files/ls", timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"❌ List failed: {e}")
        return None

# ============== TEST CODE ==============
if __name__ == "__main__":
    print("\n" + "="*60)
    print("📦 Testing Complete IPFS Handler")
    print("="*60)
    
    handler = IPFSHandler()
    
    if handler.test_connection():
        # Test text upload/download
        print("\n📝 Test 1: Text Upload/Download")
        test_text = "Hello IPFS! This is a secure message from IoT Blockchain system. Timestamp: " + str(os.time())
        result = handler.upload_text(test_text)
        
        if result:
            print(f"✅ Upload successful! CID: {result['ipfs_cid']}")
            
            downloaded = handler.download_text(result['ipfs_cid'])
            if downloaded == test_text:
                print("✅ Download successful! Text matches!")
            else:
                print("❌ Download mismatch!")
        
        # Test file upload (if test file exists)
        print("\n📁 Test 2: File Upload/Download")
        test_file = "/tmp/test_ipfs.txt"
        with open(test_file, 'w') as f:
            f.write("This is a test file for IPFS")
        
        result = handler.upload_file(test_file)
        if result:
            print(f"✅ File upload successful! CID: {result['ipfs_cid']}")
        
        print("\n" + "="*60)
        print("🎉 IPFS Handler is ready!")
        print("="*60)
    else:
        print("\n❌ Make sure IPFS daemon is running: ipfs daemon")