# data_generator.py
import uuid
import hashlib

def generate_secret_key():
    """
    Generate secret key for a device.
    Returns:
        secret_key (str) : unhashed key (optional for device internal use)
        secret_hash (str): hashed key for database storage
    """
    # Step 1: Generate random UUID as secret key
    secret_key = uuid.uuid4().hex  # 32-character random key
    
    # Step 2: Hash the secret key for DB storage
    secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()
    
    # Step 3: Notification
    print(f"Secret key created: {secret_key}")
    
    # Step 4: Return both
    return secret_key, secret_hash