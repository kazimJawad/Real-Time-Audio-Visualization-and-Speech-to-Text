import numpy as np

class DBCalculator:
    def __init__(self, reference_level=-100, min_db=0, max_db=120):
        self.reference_level = reference_level
        self.min_db = min_db
        self.max_db = max_db

    def calculate_db(self, data):
        if len(data) == 0:
            return self.min_db

        rms = np.sqrt(np.mean(np.square(data)))
        if rms == 0:
            return self.min_db

        db = 20 * np.log10(rms) - self.reference_level
        db = max(self.min_db, min(db, self.max_db))  # Clamp values to min_db and max_db
        return db