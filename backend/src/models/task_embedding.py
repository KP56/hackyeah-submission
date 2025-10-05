# task_embedding.py
from datetime import datetime
import numpy as np

class TaskEmbeddingFactory:
    def __init__(self, text_embedding_model):
        """
        :param text_embedding_model: Instance of a class with an encode(text) -> np.ndarray method
        """
        self.text_embedding_model = text_embedding_model

    def create_embedding(self, text: str, date: datetime) -> np.ndarray:
        """
        Combines text embedding with date features into a single vector.
        :param text: Input text
        :param date: datetime object
        :return: numpy array of concatenated embedding
        """
        # Extract date features
        day_of_week = date.weekday()  # Monday=0, Sunday=6
        hour = date.hour

        # Get text embedding
        text_vector = self.text_embedding_model.encode(text)

        # Concatenate into single vector
        combined_vector = np.concatenate([text_vector, np.array([day_of_week, hour], dtype=np.float32)])
        return combined_vector
