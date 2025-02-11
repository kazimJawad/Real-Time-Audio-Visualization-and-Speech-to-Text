# Overview
This project is an interactive dashboard that provides real-time audio signal visualization and speech-to-text transcription. It allows users to:
- Monitor and visualize live audio data in real-time.
- View key audio features like dB level, waveform, and spectrogram.
- Convert live audio into text using speech recognition.
- Save the captured data (including audio statistics and transcriptions) to a CSV file.
- The dashboard is built using Dash (for the web interface) and integrates with Python libraries such as Plotly for graphing, pyaudio for real-time audio stream handling, and SpeechRecognition for transcription.

# Features
-	Real-Time Audio Visualization: Displays dB levels, waveform, and spectrogram of live audio data.
-	Speech-to-Text Transcription: Uses Google's Speech Recognition API to transcribe spoken words into text.
-	Data Logging: Captures and saves audio statistics (dB levels, waveform, spectrogram) and transcriptions in a CSV file.
-	Device Selection: Allows the user to select an audio input device for capturing live data.
-	Interactive Controls: Start/Stop transcription, start/stop data saving, and choose the input device.
-	Real-Time Updates: The graphs and transcription display update in real-time as audio data is received.


# Tech Stack
•	Dash: Web framework for building interactive web applications.
•	Plotly: For creating interactive visualizations (dB levels, waveform, spectrogram).
•	SpeechRecognition: For converting audio to text.
•	pyaudio: For capturing audio input.
•	NumPy: For handling numerical operations such as calculating dB levels.
•	CSV: For saving captured data into a CSV file.
•	Threading: Used for handling real-time audio streaming and background tasks (like data saving).
