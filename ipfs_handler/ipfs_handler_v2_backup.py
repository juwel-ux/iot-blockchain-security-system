import requests
import json
import hashlib
import os

class IPFSHandler:
    def __init__(self):
        self.api_url = "http://127.0.0.1:5001/api/v0"
    
    def upload_text(self, text):
        """Upload text to IPFS using HTTP API"""
        try:
            files = {'file': ('text.txt', text.encode('utf-8'))}
            response = requests.post(f"{self.api_url}/add", files=files)
            
            if response.status_code == 200:
                result = response.json()
                ipfs_cid = result['Hash']
                data_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                
                print(f"📤 Uploaded to IPFS:")
                print(f"   CID: {ipfs_cid}")
                print(f"   Hash: {data_hash[:32]}...")
                
                return {
                    'ipfs_cid': ipfs_cid,
                    'data_hash': data_hash,
                    'size': len(text)
                }
        except Exception as e:
            print(f"❌ Upload failed: {e}")
        return None
    
    def upload_file(self, file_path):
        """Upload file to IPFS using HTTP API"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                response = requests.post(f"{self.api_url}/add", files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    ipfs_cid = result['Hash']
                    
                    # Get file hash
                    f.seek(0)
                    data_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    print(f"📤 Uploaded file to IPFS:")
                    print(f"   File: {file_path}")
                    print(f"   CID: {ipfs_cid}")
                    print(f"   Hash: {data_hash[:32]}...")
                    
                    return {
                        'ipfs_cid': ipfs_cid,
                        'data_hash': data_hash,
                        'size': os.path.getsize(file_path),
                        'filename': os.path.basename(file_path)
                    }
        except Exception as e:
            print(f"❌ Upload failed: {e}")
        return None
    
    def download_text(self, ipfs_cid):
        """Download text from IPFS using HTTP API"""
        try:
            response = requests.post(f"{self.api_url}/cat", params={'arg': ipfs_cid})
            if response.status_code == 200:
                text = response.text
                print(f"📥 Downloaded from IPFS: {ipfs_cid}")
                return text
        except Exception as e:
            print(f"❌ Download failed: {e}")
        return None
    
    def download_file(self, ipfs_cid, output_path):
        """Download file from IPFS using HTTP API"""
        try:
            response = requests.post(f"{self.api_url}/cat", params={'arg': ipfs_cid})
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"📥 Downloaded file to: {output_path}")
                return True
        except Exception as e:
            print(f"❌ Download failed: {e}")
        return False
    
    def test_connection(self):
        """Test IPFS connection"""
        try:
            response = requests.post(f"{self.api_url}/version")
            if response.status_code == 200:
                version = response.json()
                print(f"✅ IPFS Connected! Version: {version.get('Version')}")
                return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Testing IPFS Handler v2")
    print("="*50)
    
    handler = IPFSHandler()
    
    if handler.test_connection():
        # Test text upload
        result = handler.upload_text("Hello, this is a test message for IoT Blockchain!")
        if result:
            print(f"\n✅ Text uploaded successfully!")
            print(f"   CID: {result['ipfs_cid']}")
            
            # Test download
            downloaded = handler.download_text(result['ipfs_cid'])
            if downloaded:
                print(f"✅ Downloaded: {downloaded[:50]}...")
    else:
        print("❌ Make sure IPFS daemon is running: ipfs daemon")
