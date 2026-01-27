import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.core.config import settings


logger = logging.getLogger(__name__)


class MemoryService:
    """
    Manages vector embeddings and memory storage using ChromaDB
    """

    def __init__(self):
        self.collection: Optional[chromadb.Collection] = None
        self.embedder: Optional[SentenceTransformer] = None
        self.client: Optional[chromadb.ClientAPI] = None

    def initialize(self) -> None:
        """Initialize ChromaDB and load embedding model"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(settings.memory_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="conversations",
                metadata={"hnsw:space": "cosine"},
            )

            # Load embedding model
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self.embedder = SentenceTransformer(settings.embedding_model)
            logger.info("Memory service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}", exc_info=True)
            raise

    def add_memory(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a memory to the vector store

        Args:
            text: The text to store
            metadata: Optional metadata dict

        Returns:
            Memory ID (UUID string)
        """
        if not self.collection or not self.embedder:
            raise RuntimeError("Memory service not initialized")

        # Generate embedding
        embedding = self.embedder.encode(text).tolist()

        # Generate ID
        import uuid
        memory_id = str(uuid.uuid4())

        # Store in ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata] if metadata else [{}],
        )

        logger.debug(f"Added memory: {memory_id}")
        return memory_id

    def search_memory(self, query: str, n_results: int = 3) -> List[str]:
        """
        Search for similar memories

        Args:
            query: Search query text
            n_results: Number of results to return

        Returns:
            List of matching document texts
        """
        if not self.collection or not self.embedder:
            logger.warning("Memory service not initialized, returning empty results")
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedder.encode(query).tolist()

            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
            )

            # Extract documents
            documents = results.get("documents", [])
            if documents and len(documents) > 0:
                return documents[0]  # Return first (and only) query result list
            return []

        except Exception as e:
            logger.error(f"Memory search failed: {e}", exc_info=True)
            return []


# Global instance
memory = MemoryService()

# Initialize on import
try:
    memory.initialize()
except Exception as e:
    logger.error(f"Failed to initialize memory on import: {e}")
