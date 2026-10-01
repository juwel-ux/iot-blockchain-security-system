# db_handler.py
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  # adjust if using username/password
db = client["iot_project_db"]
devices_collection = db["devices"]


def add_device(device_id, device_type, secret_hash=None):
    """
    Add a device to MongoDB
    """
    device_doc = {
        "device_id": device_id,
        "device_type": device_type,
        "secret_hash": secret_hash
    }
    
    result = devices_collection.insert_one(device_doc)
    print(f"Device added to MongoDB: {device_id}")
    return result.inserted_id