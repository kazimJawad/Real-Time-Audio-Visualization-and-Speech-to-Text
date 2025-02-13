import pygame
import numpy as np
import colorsys

class Visualizer:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Audio Waveform Visualizer")
        self.font = pygame.font.Font(None, 36)

    def update(self, audio_data, db_level):
        self.screen.fill((0, 0, 0))  # Clear the screen with black

        # Normalize audio data for visualization
        audio_data = np.interp(audio_data, [-1, 1], [0, self.height])  # Map the audio data to screen height

        # Generate dynamic color based on dB level
        color = self.get_color_for_db(db_level)

        # Draw the waveform with the dynamic color
        self.draw_waveform(audio_data, color)

        # Display dB level as text
        text = self.font.render(f"{db_level:.2f} dB", True, (255, 255, 255))
        self.screen.blit(text, (10, 10))

        pygame.display.flip()

    def get_color_for_db(self, db):
        # Create a hue-shifted color based on dB level (normalized to range [0, 1])
        normalized_db = max(0, min(db, 120)) / 120.0  # Assuming max dB is 120
        hue = (1.0 - normalized_db) * 0.33  # From red (high dB) to green (low dB)
        rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        return tuple(int(255 * x) for x in rgb)  # Convert to 255 scale

    def draw_waveform(self, audio_data, color):
        center_y = self.height // 2

        # Calculate step to skip audio data to fit the screen width
        step_size = max(1, len(audio_data) // self.width)

        # Create a glow/shadow effect for the waveform
        shadow_color = (50, 50, 50)  # A dark shadow color

        # Draw the shadow first (slightly offset)
        for x in range(0, self.width):
            y_value = int(audio_data[x * step_size])
            pygame.draw.line(self.screen, shadow_color, (x, center_y + 5), (x, y_value + 5), 3)

        # Draw the waveform itself with dynamic color
        for x in range(0, self.width):
            y_value = int(audio_data[x * step_size])
            pygame.draw.line(self.screen, color, (x, center_y), (x, y_value), 2)

    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True
