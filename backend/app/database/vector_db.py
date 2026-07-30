import json
import os
import numpy as np
from typing import List, Dict, Tuple, Optional
from backend.app.config import settings

class VectorDB:
    def __init__(self):
        self.chunks_path = settings.DB_DIR / "corpus.json"
        self.embeddings_path = settings.DB_DIR / "embeddings.npy"
        
        self.chunks: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        
        # Load database if it already exists
        self.load()

    def save(self, chunks: List[Dict], embeddings: np.ndarray) -> None:
        """
        Saves chunks metadata and dense embeddings to disk.
        """
        self.chunks = chunks
        self.embeddings = embeddings
        
        # Save chunks as JSON
        with open(self.chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
            
        # Save embeddings as .npy
        np.save(self.embeddings_path, embeddings)

    def load(self) -> Tuple[List[Dict], Optional[np.ndarray]]:
        """
        Loads chunks metadata and embeddings from disk.
        """
        if self.chunks_path.exists():
            with open(self.chunks_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
        else:
            self.chunks = []

        if self.embeddings_path.exists():
            self.embeddings = np.load(self.embeddings_path)
        else:
            self.embeddings = None

        return self.chunks, self.embeddings

    def is_empty(self) -> bool:
        """
        Checks if the database is empty.
        """
        return len(self.chunks) == 0 or self.embeddings is None

# Singleton instance of VectorDB
vector_db = VectorDB()
