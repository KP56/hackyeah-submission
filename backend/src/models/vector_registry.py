import os
import pickle
import numpy as np


class VectorRegistry:
    """
    A simple registry for storing and managing NumPy vectors.
    Provides functionality to add, save, and load vectors from disk.
    """

    def __init__(self, filename: str = "vectors.pkl"):
        """
        Initialize the registry.

        Args:
            filename (str): Name of the file where vectors are serialized.
        """
        self.data_dir = "data"
        self.filepath = os.path.join(self.data_dir, filename)
        self.vectors = []

        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)

    def add(self, vector: np.ndarray):
        """
        Add a NumPy vector to the registry.

        Args:
            vector (np.ndarray): The vector to be added.
        """
        if not isinstance(vector, np.ndarray):
            raise TypeError("Only numpy.ndarray objects can be added.")
        self.vectors.append(vector)

    def save(self):
        """
        Serialize and save the vectors to disk.
        """
        with open(self.filepath, "wb") as f:
            pickle.dump(self.vectors, f)
        print(f"Saved {len(self.vectors)} vectors to {self.filepath}")

    def load(self):
        """
        Load vectors from disk into the registry.
        """
        if not os.path.exists(self.filepath):
            print(f"No saved file found at {self.filepath}. Starting with an empty registry.")
            self.vectors = []
            return

        with open(self.filepath, "rb") as f:
            self.vectors = pickle.load(f)
        print(f"Loaded {len(self.vectors)} vectors from {self.filepath}")

    def __len__(self):
        """Return the number of vectors in the registry."""
        return len(self.vectors)

    def __getitem__(self, idx):
        """Access a vector by index."""
        return self.vectors[idx]
