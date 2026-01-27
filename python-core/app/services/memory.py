import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from app.core.config import settings
import uuid
import logging


logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages local vector memory using ChromaDB and sentence-transformers"""

    def __init__(self):
        try:
            # Initialize ChromaDB in persistent mode
            logger.info(f"Initializing ChromaDB at: {settings.memory_dir}")
            self.client = chromadb.PersistentClient(
                path=str(settings.memory_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="chat_memory",
                metadata={"hnsw:space": "cosine"},  # Cosine similarity
            )

            # Load local embedding model (runs on CPU)
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self.embedder = SentenceTransformer(settings.embedding_model)

            logger.info("Memory system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize memory: {e}")
            raise

    def add_memory(self, text: str, metadata: dict | None = None) -> str | None:
        """
        Add a memory to the vector database

        Args:
            text: The text to remember
            metadata: Optional metadata (e.g., timestamp, model, query_type)

        Returns:
            memory_id: UUID of the stored memory
        """
        try:
            # Generate embedding locally (no API call)
            embedding = self.embedder.encode(text).tolist()

            memory_id = str(uuid.uuid4())

            self.collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}],
                ids=[memory_id],
            )

            logger.debug(f"Added memory: {memory_id[:8]}...")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return None

    def search_memory(self, query: str, n_results: int = 3) -> list[str]:
        """
        Search for relevant memories using semantic similarity

        Args:
            query: The search query
            n_results: Number of results to return

        Returns:
            List of relevant memory texts
        """
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode(query).tolist()

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
            )

            # Extract documents
            if results["documents"] and len(results["documents"]) > 0:
                memories = results["documents"][0]
                logger.debug(f"Found {len(memories)} relevant memories")
                return memories

            return []

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    def clear_all(self) -> None:
        """Clear all memories (use with caution!)"""
        try:
            self.client.delete_collection("chat_memory")
            self.collection = self.client.create_collection("chat_memory")
            logger.info("All memories cleared")
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")


# Global instance
memory = MemoryManager()

