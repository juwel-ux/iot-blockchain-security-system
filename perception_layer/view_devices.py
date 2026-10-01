from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["iot_project_db"]
devices_collection = db['devices']

# Fetch all devices
devices = devices_collection.find()
print("All devices in MongoDB:\n")
for d in devices:
    print(f"Device ID: {d.get('device_id')}, Type: {d.get('device_type')}, Created at: {d.get('timestamp')}")