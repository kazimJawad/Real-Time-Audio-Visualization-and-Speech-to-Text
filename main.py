from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import numpy as np
from collections import deque
import csv
import os
from datetime import datetime
from audio_input import AudioInput
from db_calculator import DBCalculator
from device_manager import DeviceManager
import pyaudio
import threading
import speech_recognition as sr

# Initialize the Dash app
app = Dash(__name__, suppress_callback_exceptions=True)

# Initialize device manager and list input devices
device_manager = DeviceManager()
devices = device_manager.list_devices()
device_options = [{"label": device["name"], "value": device["index"]} for device in devices]
selected_device_index = None  # To persist the selected device index

# Initialize data structures and threading lock
db_values = deque(maxlen=50)
waveform_data = deque(maxlen=1024)  # For waveform visualization
spectrogram_frame = None  # Single frame of FFT magnitudes
transcription_log = []  # To store transcription history
data_lock = threading.Lock()
transcription_active = False  # Control start/stop of speech recognition
data_saving_active = False  # Control start/stop of data saving

# Initialize dB calculator
db_calculator = DBCalculator(reference_level=-100, min_db=0, max_db=120)
audio = None  # Will be initialized upon device selection

# Initialize speech recognizer
recognizer = sr.Recognizer()

# CSV file path
csv_file_path = r"D:/university/Semester 4/RT/Project/audio visualizer/audio_data.csv"

# Ensure the directory exists
def ensure_directory_exists():
    directory = os.path.dirname(csv_file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

# Initialize CSV file with headers
def initialize_csv():
    ensure_directory_exists()
    if not os.path.isfile(csv_file_path):
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp", "dB Level", "Mean dB", "Peak dB",
                "Std Dev dB", "Waveform Data", "Spectrogram Data", "Transcription"
            ])

# Save data to CSV
def save_data_to_csv():
    with data_lock:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db_level = db_values[-1] if db_values else "N/A"
        mean_db = np.mean(db_values) if db_values else "N/A"
        peak_db = np.max(db_values) if db_values else "N/A"
        std_dev_db = np.std(db_values) if db_values else "N/A"
        waveform = list(waveform_data) if waveform_data else []
        spectrogram = list(spectrogram_frame) if spectrogram_frame is not None else []
        transcription = " ".join(transcription_log)

        with open(csv_file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, db_level, mean_db, peak_db, std_dev_db, waveform, spectrogram, transcription])

# Initialize CSV at the start
initialize_csv()

# Periodic data saving thread
def data_saving_thread():
    global data_saving_active
    while data_saving_active:
        save_data_to_csv()
        threading.Event().wait(1)  # Save every 1 second

# Main layout with tabs
app.layout = html.Div([
    html.H1("Real-Time Audio Visualization & Speech to Text", style={'textAlign': 'center', 'marginBottom': '20px'}),

    dcc.Tabs(id="tabs", value='project', children=[
        dcc.Tab(label='Project', value='project'),
        dcc.Tab(label='Documentation', value='documentation')
    ]),

    html.Div(id='tabs-content')
])

# Layout for the project tab
def project_layout():
    return html.Div([
        html.Div([
            html.Label("Select Input Device:", style={'fontSize': '18px'}),
            dcc.Dropdown(id="device-dropdown", options=device_options, value=selected_device_index,
                         style={'width': '50%', 'margin': 'auto'}),
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),

        html.Div([
            html.H2("Current dB Level", style={'textAlign': 'center'}),
            html.Div(id="current-db-display", style={'fontSize': '48px', 'textAlign': 'center'}),

            html.H3("Statistics", style={'textAlign': 'center', 'marginTop': '30px'}),
            html.Div(id="statistics-display", style={'fontSize': '20px', 'color': 'green', 'textAlign': 'center'}),

            dcc.Graph(id="db-level-graph", animate=False, style={'height': '30vh', 'marginTop': '20px'}),
        ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top',
                  'padding': '20px', 'borderRight': '2px solid #ccc'}),

        html.Div([
            dcc.Graph(id="waveform-graph", animate=False, style={'height': '30vh'}),
            dcc.Graph(id="spectrogram-graph", animate=False, style={'height': '30vh', 'marginTop': '20px'}),
        ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top',
                  'padding': '20px'}),

        html.Div([
            html.H2("Real-Time Speech-to-Text", style={'textAlign': 'center'}),
            html.Div(id="transcription-display", style={
                'fontSize': '20px', 'textAlign': 'left', 'whiteSpace': 'pre-wrap', 'padding': '10px',
                'border': '1px solid #ccc', 'height': '50vh', 'overflowY': 'scroll'
            }),

            html.Button("Start Transcription", id="start-button", n_clicks=0, style={'margin': '10px'}),
            html.Button("Stop Transcription", id="stop-button", n_clicks=0, style={'margin': '10px'}),
            html.Button("Start Data Saving", id="start-data-saving", n_clicks=0, style={'margin': '10px'}),
            html.Button("Stop Data Saving", id="stop-data-saving", n_clicks=0, style={'margin': '10px'}),
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top',
                  'padding': '10px'}),

        dcc.Interval(
            id="graph-update",
            interval=200,  # Update every 200ms
            n_intervals=0,
            disabled=True  # Disabled until a device is selected
        ),
        dcc.Interval(
            id="transcription-update",
            interval=2000,  # Update transcription display every 2 seconds
            n_intervals=0
        )
    ])

# Layout for the documentation tab
def documentation_layout():
    return html.Div([
        html.H2("📘 Project Documentation", style={'textAlign': 'center', 'marginBottom': '30px', 'color': '#4CAF50', 'fontSize': '36px', 'fontWeight': 'bold'}),

        # Introduction Section
        html.Div([
            html.H3("🌟 Introduction", style={'color': '#FF5733', 'marginTop': '20px', 'fontSize': '28px'}),
            html.P("This interactive Dashboard allows us to "
                   "monitor and analyze live audio signals, convert into text through speech recognition, and log relevant data for "
                   "further analysis. Whether an acoustic researcher, a sound engineer, or simply someone interested in audio analytics, "
                   "this dashboard equiped with the tools to visualize, record, and process audio data in real-time, all within an easy-to-use interface.",
                   style={'lineHeight': '1.6', 'textAlign': 'justify', 'fontSize': '18px', 'color': '#333'}),
            html.Div(html.Img(src='/assets/System Arctitecture diagram.png', style={'width': '50%', 'marginTop': '10px'}),
                     style={'textAlign': 'center'}),  # Placeholder for a figure
        ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)', 'backgroundColor': '#f9f9f9', 'marginBottom': '20px'}),

        # Key Features Section
        html.Div([
            html.H3("💡 Key Features", style={'color': '#2196F3', 'marginTop': '20px', 'fontSize': '28px'}),
            html.Ul([
                html.Li("📊 Real-Time Audio Visualization: Continuously monitor the dB levels, waveform, and spectrogram as the audio signal flows in. "
                        "This helps us to understand the frequency and amplitude of the signal as it evolves.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("📝 Speech-to-Text Transcription: The dashboard leverages Google's Speech Recognition API to convert live audio into text. "
                        "This is a great way to capture conversations or live audio content in text form.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("💾 Data Logging: Data, including audio statistics (e.g., dB levels, waveform, spectrogram) and transcriptions, are saved to a CSV file. "
                        "This allows to track and analyze the data later on.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("🎛 Interactive Controls: The interface offers easy-to-use buttons for starting/stopping transcription, starting/stopping data saving, and selecting the input device.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("📈 Dynamic Graphing: The graphs automatically update every few milliseconds, reflecting the changes in the real-time audio input.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
            ], style={'paddingLeft': '20px', 'fontSize': '18px'}),
        ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)', 'backgroundColor': '#f9f9f9', 'marginBottom': '20px'}),

        # How It Works Section
        html.Div([
            html.H3("🔧 How It Works", style={'color': '#8E44AD', 'marginTop': '20px', 'fontSize': '28px'}),
            html.P("This dashboard integrates several components to deliver real-time audio processing and transcription. Here's a step-by-step breakdown of how everything works:",
                   style={'lineHeight': '1.6', 'fontSize': '18px'}),
            html.Ol([
                html.Li("📡 Audio Input Processing: The system captures audio data from the selected device. This raw audio data is then processed to calculate essential audio features like volume (dB levels).",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("📊 Real-Time Visualization: The processed audio data is used to generate real-time graphs for dB levels, waveform, and spectrogram. The graphs automatically update to reflect changes in the audio signal.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("📝 Speech-to-Text Conversion: The captured audio is passed to Google’s Speech Recognition API, which converts it into text. This text is stored in the system for later use or analysis.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("💾 Data Logging: Every second, the system writes the latest audio data and transcription logs to a CSV file. This makes the data accessible for future analysis.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
            ], style={'paddingLeft': '20px', 'fontSize': '18px'}),
        ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)', 'backgroundColor': '#f9f9f9', 'marginBottom': '20px'}),

        # User Guide Section
        html.Div([
            html.H3("👨‍💻 User Guide", style={'color': '#FFC107', 'marginTop': '20px', 'fontSize': '28px'}),
            html.Ol([
                html.Li("🔌 Step 1: Connect microphone or audio input device to your computer.", style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("💻 Step 2: Open the dashboard and select your desired input device from the dropdown menu.", style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("📊 Step 3: View real-time audio data as dB levels, waveform, and spectrogram graphs.", style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("📝 Step 4: Press 'Start Transcription' to convert live audio into text. Press 'Stop Transcription' when you want to stop the conversion.", style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("💾 Step 5: Press 'Start Data Saving' to begin logging the audio statistics and transcriptions into a CSV file. You can stop data saving at any time.",
                        style={'lineHeight': '1.8', 'fontSize': '18px'}),
            ], style={'paddingLeft': '20px', 'fontSize': '18px'}),
        ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)', 'backgroundColor': '#f9f9f9', 'marginBottom': '20px'}),

        # Challenges and Mitigations Section
        html.Div([
            html.H3("⚠️ Challenges and Mitigations", style={'color': '#E74C3C', 'marginTop': '20px', 'fontSize': '28px'}),
            html.Table([
                html.Tr([html.Th("Challenge", style={'borderBottom': '2px solid #ddd', 'padding': '8px'}),
                         html.Th("Solution", style={'borderBottom': '2px solid #ddd', 'padding': '8px'})]),
                html.Tr([html.Td("⚡ Real-Time Data Handling", style={'padding': '8px', 'textAlign': 'center'}),
                         html.Td("🛠 Utilize threading and locks for seamless updates of graphs and real-time data.", style={'padding': '8px', 'textAlign': 'center'})]),
                html.Tr([html.Td("📱 Device Initialization", style={'padding': '8px', 'textAlign': 'center'}),
                         html.Td("🔄 Implement a dynamic dropdown menu to select the device and initialize it.", style={'padding': '8px', 'textAlign': 'center'})]),
                html.Tr([html.Td("💾 Data Logging", style={'padding': '8px', 'textAlign': 'center'}),
                         html.Td("🔐 Use synchronized writes to prevent data loss or corruption while saving to the CSV.", style={'padding': '8px', 'textAlign': 'center'})]),
                html.Tr([html.Td("📝 Transcription Accuracy", style={'padding': '8px', 'textAlign': 'center'}),
                         html.Td("🔧 Calibrate microphone settings and optimize noise filtering for better recognition.", style={'padding': '8px', 'textAlign': 'center'})]),
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'marginBottom': '20px', 'textAlign': 'center'}),
        ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)', 'backgroundColor': '#f9f9f9', 'marginBottom': '20px'}),

        # Future Improvements Section
        html.Div([
            html.H3("🔮 Future Improvements", style={'color': '#1ABC9C', 'marginTop': '20px', 'fontSize': '28px'}),
            html.Ul([
                html.Li("🔍 Integrate more advanced transcription models to improve accuracy and punctuation.", style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("🌐 Add cloud integration for better scalability and remote data access.", style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("🌍 Implement multi-language support for transcription.", style={'lineHeight': '1.8', 'fontSize': '18px'}),
                html.Li("💾 Implement automated backup of the data files to prevent data loss.", style={'lineHeight': '1.8', 'fontSize': '18px'}),
            ], style={'paddingLeft': '20px', 'fontSize': '18px'}),
        ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '8px', 'boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)', 'backgroundColor': '#f9f9f9'}),
    ], style={'padding': '30px', 'fontFamily': 'Arial, sans-serif'})






# Callback to switch between tabs
@app.callback(Output('tabs-content', 'children'), [Input('tabs', 'value')])
def render_tab_content(tab):
    if tab == 'project':
        return project_layout()
    elif tab == 'documentation':
        return documentation_layout()

# Function to run speech recognition
def run_speech_recognition():
    global transcription_active, transcription_log
    while transcription_active:
        try:
            with sr.Microphone() as source:
                audio_data = recognizer.listen(source, timeout=2, phrase_time_limit=20)
                phrase = recognizer.recognize_google(audio_data)
                transcription_log.append(phrase)
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            pass  # Ignore unrecognized speech
        except sr.RequestError:
            transcription_log.append("Speech recognition unavailable.")
        except Exception as e:
            print(f"Unexpected error: {e}")

# Callback to persist input device selection
@app.callback(
    Output("device-dropdown", "value"),
    [Input("device-dropdown", "value")]
)
def persist_device_selection(device_index):
    global selected_device_index
    selected_device_index = device_index
    return selected_device_index

# Callback to control transcription buttons
@app.callback(
    [Output("start-button", "disabled"),
     Output("stop-button", "disabled")],
    [Input("start-button", "n_clicks"),
     Input("stop-button", "n_clicks")]
)
def control_transcription_buttons(start_clicks, stop_clicks):
    global transcription_active
    if start_clicks > stop_clicks:
        if not transcription_active:
            transcription_active = True
            threading.Thread(target=run_speech_recognition, daemon=True).start()
        return True, False  # Disable Start button, enable Stop button
    else:
        transcription_active = False
        return False, True  # Enable Start button, disable Stop button

# Callback to control data saving
@app.callback(
    [Output("start-data-saving", "disabled"),
     Output("stop-data-saving", "disabled")],
    [Input("start-data-saving", "n_clicks"),
     Input("stop-data-saving", "n_clicks")]
)
def control_data_saving(start_clicks, stop_clicks):
    global data_saving_active
    if start_clicks > stop_clicks:
        if not data_saving_active:
            data_saving_active = True
            threading.Thread(target=data_saving_thread, daemon=True).start()
        return True, False  # Disable start button, enable stop button
    else:
        data_saving_active = False
        return False, True  # Enable start button, disable stop button

# Callback to update transcription display
@app.callback(
    Output("transcription-display", "children"),
    [Input("transcription-update", "n_intervals")]
)
def update_transcription_display(n_intervals):
    return "\n".join(transcription_log)

# Callback to start the audio stream when a device is selected
@app.callback(
    Output("graph-update", "disabled"),
    [Input("device-dropdown", "value")]
)
def start_audio_stream(device_index):
    global audio
    if device_index is not None:
        audio = AudioInput(device_index)

        def stream_callback(in_data, frame_count, time_info, status):
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            db_level = db_calculator.calculate_db(audio_data)

            with data_lock:
                db_values.append(db_level)
                waveform_data.clear()
                waveform_data.extend(audio_data[:1024])  # Limit to fixed sample size

                global spectrogram_frame
                spectrogram_frame = np.abs(np.fft.fft(audio_data)[:len(audio_data) // 2])

            return (in_data, pyaudio.paContinue)

        audio.start_stream(stream_callback)
        return False  # Enable graph updates

    return True  # Keep graph updates disabled until a device is selected

# Callback to update graphs and displays
@app.callback(
    [Output("waveform-graph", "figure"),
     Output("spectrogram-graph", "figure"),
     Output("db-level-graph", "figure"),
     Output("current-db-display", "children"),
     Output("current-db-display", "style"),
     Output("statistics-display", "children")],
    [Input("graph-update", "n_intervals")]
)
def update_graphs(n_intervals):
    with data_lock:
        db_values_copy = list(db_values)
        waveform_data_copy = list(waveform_data)
        spectrogram_frame_copy = spectrogram_frame

    # Update dB graph
    if db_values_copy:
        x_db = np.arange(len(db_values_copy))
        y_db = db_values_copy
        db_figure = {
            "data": [go.Scatter(x=x_db, y=y_db, mode="lines+markers")],
            "layout": go.Layout(title="dB Levels Over Time", xaxis=dict(title="Frames"),
                                yaxis=dict(title="dB Level", range=[0, 120]))
        }
    else:
        db_figure = {"data": [], "layout": go.Layout(title="dB Levels Over Time")}

    # Update waveform graph
    if waveform_data_copy:
        x_waveform = np.arange(len(waveform_data_copy)) * (1000 / 44100)  # Convert indices to milliseconds
        y_waveform = waveform_data_copy

        y_min = min(y_waveform) if y_waveform else -1
        y_max = max(y_waveform) if y_waveform else 1

        waveform_figure = {
            "data": [go.Scatter(x=x_waveform, y=y_waveform, mode="lines")],
            "layout": go.Layout(
                title="Waveform",
                xaxis=dict(title="Time (ms)"),
                yaxis=dict(title="Amplitude", range=[y_min * 1.1, y_max * 1.1]),
            ),
        }
    else:
        waveform_figure = {"data": [], "layout": go.Layout(title="Waveform")}

    # Update spectrogram graph
    if spectrogram_frame_copy is not None:
        freq_axis = np.fft.fftfreq(len(spectrogram_frame_copy) * 2, d=1 / 44100)[:len(spectrogram_frame_copy)]
        spectrogram_figure = {
            "data": [go.Scatter(x=freq_axis, y=spectrogram_frame_copy, mode="lines")],
            "layout": go.Layout(
                title="Spectrogram",
                xaxis=dict(title="Frequency (Hz)"),
                yaxis=dict(title="Amplitude"),
            ),
        }
    else:
        spectrogram_figure = {"data": [], "layout": go.Layout(title="Spectrogram")}

    # Update dB level and statistics
    if db_values_copy:
        current_db = db_values_copy[-1]
        db_color = "green" if current_db < 40 else "yellow" if current_db < 70 else "red"
        db_style = {"fontSize": "48px", "color": db_color, "textAlign": "center"}
        statistics = [
            html.Div(f"Mean: {np.mean(db_values_copy):.2f} dB"),
            html.Div(f"Peak: {np.max(db_values_copy):.2f} dB"),
            html.Div(f"Std Dev: {np.std(db_values_copy):.2f} dB"),
            html.Div(f"Count: {len(db_values_copy)}")
        ]
        current_db_text = f"{current_db:.2f} dB"
    else:
        current_db_text = "N/A"
        db_style = {"fontSize": "48px", "color": "black", "textAlign": "center"}
        statistics = [html.Div("No data")]

    return waveform_figure, spectrogram_figure, db_figure, current_db_text, db_style, statistics

# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True)