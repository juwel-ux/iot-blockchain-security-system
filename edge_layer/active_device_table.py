active_devices = {}

def add_device(device_id, virtual_id):

    active_devices[device_id] = virtual_id

    print("Device added to active table")

def view_devices():

    print(active_devices)