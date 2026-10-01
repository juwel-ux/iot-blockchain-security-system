# blockchain_layer/ganache_client.py
from web3 import Web3
import json

class GanacheClient:
    def __init__(self):
        # Ganache RPC URL (আপনার Ganache এ দেখাচ্ছে)
        self.rpc_url = 'http://127.0.0.1:7545'
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        if self.w3.is_connected():
            print(" Connected to Ganache Blockchain")
            print(f" RPC URL: {self.rpc_url}")
            print(f" Chain ID: {self.w3.eth.chain_id}")
            print(f" Block Number: {self.w3.eth.block_number}")
        else:
            print(" Failed to connect to Ganache")
            print(" Make sure Ganache is running")
        
        # প্রথম অ্যাকাউন্ট ব্যবহার করব
        self.accounts = self.w3.eth.accounts
        self.default_account = self.accounts[0]
        print(f"\n Default Account: {self.default_account}")
        print(f" Balance: {self.get_balance()} ETH")
    
    def get_balance(self, account=None):
        """Get balance of an account"""
        if account is None:
            account = self.default_account
        balance_wei = self.w3.eth.get_balance(account)
        return self.w3.from_wei(balance_wei, 'ether')
    
    def get_all_accounts(self):
        """Get all accounts with balances"""
        accounts_info = []
        for i, account in enumerate(self.accounts):
            accounts_info.append({
                'index': i,
                'address': account,
                'balance': float(self.get_balance(account))
            })
        return accounts_info
    
    def send_transaction(self, to_address, amount_ether, private_key=None):
        """Send ETH from default account to another address"""
        try:
            amount_wei = self.w3.to_wei(amount_ether, 'ether')
            
            transaction = {
                'to': to_address,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.default_account),
                'chainId': self.w3.eth.chain_id
            }
            
            # Note: In production, you need private key
            # For now, just return transaction details
            return {
                'status': 'ready',
                'transaction': transaction,
                'from': self.default_account,
                'to': to_address,
                'amount': amount_ether
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_transaction_count(self, account=None):
        """Get transaction count for an account"""
        if account is None:
            account = self.default_account
        return self.w3.eth.get_transaction_count(account)
    
    def get_network_info(self):
        """Get network information"""
        return {
            'chain_id': self.w3.eth.chain_id,
            'block_number': self.w3.eth.block_number,
            'gas_price': self.w3.eth.gas_price,
            'is_connected': self.w3.is_connected(),
            'peer_count': self.w3.net.peer_count
        }

# Test the connection
if __name__ == '__main__':
    print("\n" + "="*50)
    print("Ganache Client Test")
    print("="*50)
    
    client = GanacheClient()
    
    print("\n Network Info:")
    info = client.get_network_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n Accounts:")
    for acc in client.get_all_accounts():
        print(f"  [{acc['index']}] {acc['address'][:10]}... - {acc['balance']} ETH")