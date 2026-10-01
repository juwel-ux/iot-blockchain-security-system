import ipfshttpclient
import hashlib
import os

class IPFSHandler:
    def __init__(self):
        """Connect to IPFS daemon"""
        try:
            self.client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
            print("✅ IPFS Connected")
        except Exception as e:
            print(f"❌ IPFS Connection Failed: {e}")
            self.client = None
    
    def upload_text(self, text):
        """Upload text to IPFS"""
        if not self.client:
            return None
        
        data = text.encode('utf-8')
        res = self.client.add_bytes(data)
        ipfs_cid = res
        data_hash = hashlib.sha256(data).hexdigest()
        
        print(f"📤 Uploaded to IPFS:")
        print(f"   CID: {ipfs_cid}")
        print(f"   Hash: {data_hash[:32]}...")
        
        return {
            'ipfs_cid': ipfs_cid,
            'data_hash': data_hash,
            'size': len(data)
        }
    
    def download_text(self, ipfs_cid):
        """Download text from IPFS"""
        if not self.client:
            return None
        
        try:
            data = self.client.cat(ipfs_cid)
            text = data.decode('utf-8')
            print(f"📥 Downloaded from IPFS: {ipfs_cid}")
            return text
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None
    
    def test_connection(self):
        """Test IPFS connection"""
        if not self.client:
            return False
        
        try:
            test_text = "Hello IPFS!"
            result = self.upload_text(test_text)
            if result:
                downloaded = self.download_text(result['ipfs_cid'])
                if downloaded == test_text:
                    print("✅ IPFS Test Passed!")
                    return True
        except Exception as e:
            print(f"❌ IPFS Test Failed: {e}")
        
        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Testing IPFS Handler")
    print("="*50)
    
    handler = IPFSHandler()
    handler.test_connection()
