import sqlite3
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Manages SQLite database for persistent chat history.
    Handles conversations and messages storage.
    """

    def __init__(self):
        """Initialize database service with connection path"""
        self.db_path = settings.db_path
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    def initialize(self) -> None:
        """Create database tables if they don't exist"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create conversations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create messages table with foreign key
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        thinking TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    )
                """)
                
                # Create index on conversation_id for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                    ON messages(conversation_id)
                """)
                
                # Create index on created_at for sorting
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_updated_at 
                    ON conversations(updated_at DESC)
                """)
                
                conn.commit()
                self._initialized = True
                logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn

    def create_conversation(self, title: str) -> str:
        """
        Create a new conversation
        
        Args:
            title: Conversation title
            
        Returns:
            Conversation UUID string
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conversations (id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (conversation_id, title, now, now))
                conn.commit()
                logger.info(f"Created conversation: {conversation_id} - {title}")
                return conversation_id
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}", exc_info=True)
            raise

    def update_conversation_title(self, conversation_id: str, title: str) -> None:
        """
        Update conversation title
        
        Args:
            conversation_id: Conversation UUID
            title: New title
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE conversations 
                    SET title = ?, updated_at = ?
                    WHERE id = ?
                """, (title, datetime.utcnow().isoformat(), conversation_id))
                
                if cursor.rowcount == 0:
                    raise ValueError(f"Conversation {conversation_id} not found")
                
                conn.commit()
                logger.info(f"Updated conversation title: {conversation_id} - {title}")
        except Exception as e:
            logger.error(f"Failed to update conversation title: {e}", exc_info=True)
            raise

    def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str, 
        thinking: Optional[str] = None
    ) -> str:
        """
        Add a message to a conversation
        
        Args:
            conversation_id: Conversation UUID
            role: 'user' or 'assistant'
            content: Message content
            thinking: Optional thinking/reasoning content (for assistant messages)
            
        Returns:
            Message UUID string
        """
        message_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert message
                cursor.execute("""
                    INSERT INTO messages (id, conversation_id, role, content, thinking, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (message_id, conversation_id, role, content, thinking, now))
                
                # Update conversation updated_at timestamp
                cursor.execute("""
                    UPDATE conversations 
                    SET updated_at = ?
                    WHERE id = ?
                """, (now, conversation_id))
                
                conn.commit()
                logger.debug(f"Added message {message_id} to conversation {conversation_id}")
                return message_id
        except sqlite3.IntegrityError as e:
            logger.error(f"Foreign key violation: {e}", exc_info=True)
            raise ValueError(f"Conversation {conversation_id} not found")
        except Exception as e:
            logger.error(f"Failed to add message: {e}", exc_info=True)
            raise

    def get_conversations(self, limit: int = 50) -> List[Dict]:
        """
        Get list of conversations (most recent first)
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation dicts
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, title, created_at, updated_at
                    FROM conversations
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}", exc_info=True)
            raise

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Get a single conversation by ID
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Conversation dict or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, title, created_at, updated_at
                    FROM conversations
                    WHERE id = ?
                """, (conversation_id,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}", exc_info=True)
            raise

    def get_messages(self, conversation_id: str) -> List[Dict]:
        """
        Get all messages for a conversation
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            List of message dicts ordered by created_at
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, conversation_id, role, content, thinking, created_at
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY created_at ASC
                """, (conversation_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get messages: {e}", exc_info=True)
            raise

    def delete_conversation(self, conversation_id: str) -> None:
        """
        Delete a conversation and all its messages (cascade delete)
        
        Args:
            conversation_id: Conversation UUID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                
                if cursor.rowcount == 0:
                    raise ValueError(f"Conversation {conversation_id} not found")
                
                conn.commit()
                logger.info(f"Deleted conversation: {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}", exc_info=True)
            raise
