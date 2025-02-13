import pyaudio

class DeviceManager:
    def __init__(self):
        self.p = pyaudio.PyAudio()

    def list_devices(self):
        devices = []
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:  # Only input devices
                devices.append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': int(device_info['defaultSampleRate'])
                })
        return devices

    def select_device(self):
        devices = self.list_devices()
        print("Available input devices:")
        for i, device in enumerate(devices):
            print(f"{i}: {device['name']} (Channels: {device['channels']}, Sample Rate: {device['sample_rate']})")
        
        while True:
            try:
                selection = int(input("Select a device by number: "))
                if 0 <= selection < len(devices):
                    return devices[selection]['index']
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def __del__(self):
        self.p.terminate()