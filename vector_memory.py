import math
import logging
from config import settings
from pinecone import Pinecone

logger = logging.getLogger("vector_memory")

class VectorMemory:
    """
    Handles Pinecone vector storage and clustering logic for the Bias Auditor.
    Falls back to in-memory if Pinecone is not configured or fails.
    """
    def __init__(self):
        self.use_pinecone = False
        self.index = None
        self.local_memory = []
        self.session_id = "default_session"

        if settings.PINECONE_API_KEY and settings.PINECONE_API_KEY != "your_pinecone_key_here":
            try:
                pc = Pinecone(api_key=settings.PINECONE_API_KEY)
                # Attempt to connect to a default index called 'devils-advocate'
                # If it doesn't exist, we fall back to local memory.
                if 'devils-advocate' in pc.list_indexes().names():
                    self.index = pc.Index('devils-advocate')
                    self.use_pinecone = True
                    logger.info("Connected to Pinecone index 'devils-advocate'.")
            except Exception as e:
                logger.warning(f"Pinecone initialization failed: {e}. Falling back to in-memory.")

    def store_vector(self, vector: list[float], metadata: dict):
        """Store a vector with its metadata."""
        if self.use_pinecone:
            try:
                vec_id = f"vec_{len(self.local_memory)}_{metadata.get('url', 'unknown')}"
                self.index.upsert(vectors=[(vec_id, vector, metadata)], namespace=self.session_id)
            except Exception as e:
                logger.error(f"Failed to upsert to Pinecone: {e}")
        
        # Always store locally to make centroid calculation easy
        self.local_memory.append({"vector": vector, "metadata": metadata})

    def get_all_vectors(self) -> list[dict]:
        """Retrieve all vectors for the current session."""
        # For simplicity, we just return the local copy of the session's vectors
        return self.local_memory

    def calculate_bias_score(self) -> float:
        """
        Mathematical Logic: Calculating the Bias Score (0-10)
        Measures the "Clustering" of perspectives in the vector space.
        Tight Cluster -> 8-10 (Echo Chamber)
        Spread Out -> 0-3 (Balanced)
        """
        if len(self.local_memory) < 2:
            return 5.0 # Neutral starting point

        vectors = [item["vector"] for item in self.local_memory]
        n = len(vectors)
        dims = len(vectors[0])

        # 1. Centroid Calculation
        centroid = [sum(vec[i] for vec in vectors) / n for i in range(dims)]

        # 2. Distance Measurement (Average Euclidean Distance from Centroid)
        total_distance = 0
        for vec in vectors:
            dist = math.sqrt(sum((vec[i] - centroid[i]) ** 2 for i in range(dims)))
            total_distance += dist
        
        avg_distance = total_distance / n

        # Assuming vectors are normalized between -1 and 1, max distance is sqrt(dims * 4)
        # For 3 dimensions, max distance is sqrt(12) ≈ 3.46
        # Let's map avg_distance to a 0-10 score.
        # Small distance -> High bias (Echo chamber)
        # Large distance -> Low bias (Balanced)
        max_dist = math.sqrt(dims * 4) / 2.0  # realistic max average distance is roughly half of absolute max
        
        # Bias Score = 10 * (1 - (avg_distance / max_dist))
        bias_score = 10.0 * (1.0 - min(avg_distance / max_dist, 1.0))
        return round(bias_score, 1)

    def get_golden_thread_similarity(self, new_vector: list[float]) -> float:
        """
        Level 3 Gatekeeper Check: Compares full content vector against the Pinecone "Golden Thread".
        We use the centroid as the Golden Thread.
        """
        if not self.local_memory:
            return 1.0 # First item is always 100% similar to an empty thread

        vectors = [item["vector"] for item in self.local_memory]
        n = len(vectors)
        dims = len(vectors[0])
        centroid = [sum(vec[i] for vec in vectors) / n for i in range(dims)]

        # Calculate cosine similarity between new_vector and centroid
        dot_product = sum(new_vector[i] * centroid[i] for i in range(dims))
        mag1 = math.sqrt(sum(new_vector[i]**2 for i in range(dims)))
        mag2 = math.sqrt(sum(centroid[i]**2 for i in range(dims)))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        similarity = dot_product / (mag1 * mag2)
        return similarity

vector_memory = VectorMemory()
