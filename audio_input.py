import pyaudio
import numpy as np

class AudioInput:
    def __init__(self, device_index=None):
        self.p = pyaudio.PyAudio()
        self.device_index = device_index if device_index is not None else self.select_device()
        self.stream = None

    def select_device(self):
        print("Available input devices:")
        for i in range(self.p.get_device_count()):
            dev_info = self.p.get_device_info_by_index(i)
            if dev_info['maxInputChannels'] > 0:
                print(f"{i}: {dev_info['name']}")
        
        while True:
            try:
                selection = int(input("Select input device by number: "))
                if 0 <= selection < self.p.get_device_count():
                    return selection
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def start_stream(self, callback):
        self.stream = self.p.open(format=pyaudio.paFloat32,
                                  channels=1,
                                  rate=44100,
                                  input=True,
                                  input_device_index=self.device_index,
                                  frames_per_buffer=1024,
                                  stream_callback=callback)
        self.stream.start_stream()

    def stop_stream(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
