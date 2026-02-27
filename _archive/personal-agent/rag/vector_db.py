import logging
import os
import pickle
import re
import shutil
from typing import Iterable

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from sklearn.neighbors import NearestNeighbors
except ImportError:
    NearestNeighbors = None

# Setup Logging
logger = logging.getLogger(__name__)

# Persistence paths
DB_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(DB_DIR, "vector_store.pkl")
BACKUP_PATH = os.path.join(DB_DIR, "vector_store.pkl.bak")


class HashingEmbedder:
    """Lightweight fallback embedder when sentence-transformers is unavailable."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        texts = list(texts)
        vectors = np.zeros((len(texts), self.dim), dtype=np.float32)
        token_pattern = re.compile(r"\w+", re.UNICODE)
        for i, text in enumerate(texts):
            for token in token_pattern.findall(text.lower()):
                idx = hash(token) % self.dim
                vectors[i, idx] += 1.0

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


class SimpleVectorDB:
    def __init__(self):
        self.documents = []
        self.embeddings = None
        self.index = None

        if SentenceTransformer is not None:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._embedding_backend = "sentence-transformers"
        else:
            self.embedding_model = HashingEmbedder()
            self._embedding_backend = "hashing-fallback"
            logger.warning(
                "sentence-transformers is not installed. "
                "Using hashing fallback embeddings (lower retrieval quality)."
            )

        self._embedding_dim = self._detect_embedding_dim()
        self.load()

    def _detect_embedding_dim(self) -> int:
        if hasattr(self.embedding_model, "get_sentence_embedding_dimension"):
            dim = self.embedding_model.get_sentence_embedding_dimension()
            if dim:
                return int(dim)
        probe = self.embedding_model.encode(["dimension probe"])
        return int(probe.shape[1])

    def _is_embedding_compatible(self, embeddings: np.ndarray) -> bool:
        return (
            isinstance(embeddings, np.ndarray)
            and embeddings.ndim == 2
            and embeddings.shape[1] == self._embedding_dim
        )

    def add_texts(self, texts):
        if not texts:
            return

        new_embeddings = self.embedding_model.encode(texts)
        if not self._is_embedding_compatible(new_embeddings):
            raise ValueError(
                f"Generated embeddings have unexpected shape: {getattr(new_embeddings, 'shape', None)}. "
                f"Expected second dimension={self._embedding_dim}."
            )

        if self.embeddings is None:
            self.documents = list(texts)
            self.embeddings = new_embeddings
        else:
            if not self._is_embedding_compatible(self.embeddings):
                logger.warning(
                    "Stored embeddings are incompatible with current embedder "
                    "(stored_shape=%s, expected_dim=%s). Resetting vector store in memory.",
                    getattr(self.embeddings, "shape", None),
                    self._embedding_dim,
                )
                self.documents = []
                self.embeddings = None
                self.index = None
                self.documents = list(texts)
                self.embeddings = new_embeddings
                self.build_index()
                self.save()
                logger.info(f"Added {len(texts)} documents. Total: {len(self.documents)}")
                return

            self.documents.extend(texts)
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

        self.build_index()
        self.save()
        logger.info(f"Added {len(texts)} documents. Total: {len(self.documents)}")

    def build_index(self):
        if self.embeddings is None or len(self.embeddings) == 0:
            self.index = None
            return

        if NearestNeighbors is None:
            # Fallback to manual cosine similarity in query()
            self.index = None
            return

        self.index = NearestNeighbors(
            n_neighbors=min(5, len(self.embeddings)),
            metric="cosine",
        )
        self.index.fit(self.embeddings)

    def query(self, query_text, k=3):
        if len(self.documents) == 0 or self.embeddings is None:
            return []

        if not self._is_embedding_compatible(self.embeddings):
            logger.warning(
                "Stored embeddings are incompatible with current embedder "
                "(stored_shape=%s, expected_dim=%s). Returning no results.",
                getattr(self.embeddings, "shape", None),
                self._embedding_dim,
            )
            return []

        query_embedding = self.embedding_model.encode([query_text])
        if not self._is_embedding_compatible(query_embedding):
            logger.warning(
                "Query embedding shape mismatch: got %s expected dim=%s.",
                getattr(query_embedding, "shape", None),
                self._embedding_dim,
            )
            return []
        n_neighbors = min(k, len(self.documents))

        if self.index is not None:
            _, indices = self.index.kneighbors(query_embedding, n_neighbors=n_neighbors)
            return [self.documents[idx] for idx in indices[0]]

        # Fallback cosine similarity path (when sklearn is unavailable).
        q = query_embedding[0]
        dot = np.dot(self.embeddings, q)
        denom = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(q)
        denom[denom == 0] = 1.0
        sim = dot / denom
        indices = np.argsort(sim)[::-1][:n_neighbors]
        return [self.documents[idx] for idx in indices]

    def save(self):
        try:
            if os.path.exists(DATA_PATH):
                shutil.copy2(DATA_PATH, BACKUP_PATH)
                logger.debug("Backup created successfully.")

            with open(DATA_PATH, "wb") as f:
                pickle.dump({"documents": self.documents, "embeddings": self.embeddings}, f)
            logger.info("Vector Store saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save Vector Store: {e}")

    def load(self):
        if os.path.exists(DATA_PATH):
            try:
                with open(DATA_PATH, "rb") as f:
                    data = pickle.load(f)
                    self.documents = data["documents"]
                    self.embeddings = data["embeddings"]
                    if self.embeddings is not None and not self._is_embedding_compatible(self.embeddings):
                        logger.warning(
                            "Existing Vector Store embeddings are incompatible with current embedder "
                            "(stored_shape=%s, expected_dim=%s). Starting with empty DB.",
                            getattr(self.embeddings, "shape", None),
                            self._embedding_dim,
                        )
                        self.documents = []
                        self.embeddings = None
                        self.index = None
                        return
                    self.build_index()
                logger.info("Vector Store loaded from primary file.")
            except Exception as e:
                logger.error(f"Primary DB file corrupted: {e}. Attempting recovery from backup...")
                self._recover_from_backup()
        else:
            logger.info("No existing Vector Store found. Starting fresh.")

    def _recover_from_backup(self):
        if os.path.exists(BACKUP_PATH):
            try:
                with open(BACKUP_PATH, "rb") as f:
                    data = pickle.load(f)
                    self.documents = data["documents"]
                    self.embeddings = data["embeddings"]
                    if self.embeddings is not None and not self._is_embedding_compatible(self.embeddings):
                        logger.warning(
                            "Backup Vector Store is incompatible with current embedder "
                            "(stored_shape=%s, expected_dim=%s). Resetting DB.",
                            getattr(self.embeddings, "shape", None),
                            self._embedding_dim,
                        )
                        self.documents = []
                        self.embeddings = None
                        self.index = None
                        return
                    self.build_index()
                logger.warning("Restored Vector Store from backup.")
                shutil.copy2(BACKUP_PATH, DATA_PATH)
            except Exception as e:
                logger.critical(f"Backup file is also corrupted! Data loss imminent: {e}")
                self.documents = []
                self.embeddings = None
                self.index = None
        else:
            logger.error("No backup file found. Starting with empty DB.")


_db_instance = None


def get_vector_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = SimpleVectorDB()
    return _db_instance


def add_documents_to_db(chunks):
    db = get_vector_db()
    db.add_texts(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = get_vector_db()
