from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["iot_database"]
devices = db["devices"]

def InitialLightweightZero(packet):

    device_id = packet["device_id"]

    print("Packet received from:", device_id)

    device = devices.find_one({"device_id": device_id})

    if device:
        print("Device verified")

        return True

    else:
        print("Invalid device detected")

        return False