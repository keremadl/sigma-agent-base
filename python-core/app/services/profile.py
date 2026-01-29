import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from sentence_transformers import SentenceTransformer
import numpy as np
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Structured user profile management with anti-hallucination safeguards
    """
    
    def __init__(self):
        self.profile_path = settings.app_data_dir / "user_profile.json"
        self.embedder = None  # Lazy load to avoid startup delay
        self._ensure_profile_exists()
    
    def _get_embedder(self):
        """Lazy load embedder on first use"""
        if self.embedder is None:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        return self.embedder
    
    def _ensure_profile_exists(self):
        """Create empty profile if doesn't exist"""
        if not self.profile_path.exists():
            self._save({
                "entries": [],
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "total_entries": 0
                }
            })
    
    def _load(self) -> dict:
        """Load profile from disk"""
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"entries": [], "metadata": {"created": datetime.now().isoformat(), "total_entries": 0}}
    
    def _save(self, data: dict):
        """Save profile to disk"""
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_entry(self, category: str, key: str, value: str, 
                  source: str = "user_input", importance: int = 5) -> str:
        """
        Add new memory entry
        
        Args:
            category: personal, family, tech, work, preferences
            key: Short identifier (e.g., "name", "device")
            value: Actual information
            source: Where this info came from
            importance: 0-10, higher = more critical
        
        Returns:
            entry_id
        """
        profile = self._load()
        
        entry_id = f"mem_{uuid.uuid4().hex[:8]}"
        entry = {
            "id": entry_id,
            "category": category,
            "key": key,
            "value": value,
            "source": source,
            "importance": max(0, min(10, importance)),  # Clamp 0-10
            "timestamp": datetime.now().isoformat()
        }
        
        profile["entries"].append(entry)
        profile["metadata"]["total_entries"] = len(profile["entries"])
        self._save(profile)
        
        logger.info(f"Added memory: {key} (importance={importance})")
        return entry_id
    
    def get_all_entries(self, min_importance: int = 0) -> List[dict]:
        """Get all entries, optionally filtered by importance"""
        profile = self._load()
        entries = profile.get("entries", [])
        
        if min_importance > 0:
            entries = [e for e in entries if e['importance'] >= min_importance]
        
        return entries
    
    def delete_entry(self, entry_id: str) -> bool:
        """Delete a memory entry"""
        profile = self._load()
        entries = profile["entries"]
        
        initial_count = len(entries)
        profile["entries"] = [e for e in entries if e["id"] != entry_id]
        
        if len(profile["entries"]) < initial_count:
            profile["metadata"]["total_entries"] = len(profile["entries"])
            self._save(profile)
            logger.info(f"Deleted memory: {entry_id}")
            return True
        
        return False
    
    def update_entry(self, entry_id: str, new_value: str) -> bool:
        """Update a memory's value"""
        profile = self._load()
        
        for entry in profile["entries"]:
            if entry["id"] == entry_id:
                entry["value"] = new_value
                entry["last_modified"] = datetime.now().isoformat()
                self._save(profile)
                logger.info(f"Updated memory: {entry_id}")
                return True
        
        return False
    
    def get_relevant_memories(self, query: str, max_results: int = 5, 
                            max_tokens: int = 300) -> List[dict]:
        """
        SMART RETRIEVAL: Get only relevant memories within token budget
        
        This is THE KEY function that prevents hallucination!
        """
        entries = self.get_all_entries(min_importance=3)  # Drop trivial items
        
        if not entries:
            return []
        
        embedder = self._get_embedder()
        
        # Step 1: Semantic similarity scoring
        query_embedding = embedder.encode(query)
        scored = []
        
        for entry in entries:
            entry_embedding = embedder.encode(entry['value'])
            similarity = float(np.dot(query_embedding, entry_embedding))
            
            # Apply time decay (newer = better)
            try:
                age_days = (datetime.now() - datetime.fromisoformat(entry['timestamp'])).days
            except:
                age_days = 0
            decay_factor = max(0.5, 1 - (age_days * 0.01))
            
            # Combined score: similarity * importance * recency
            score = similarity * entry['importance'] * decay_factor
            scored.append((entry, score))
        
        # Step 2: Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Step 3: Enforce token budget
        selected = []
        total_tokens = 0
        
        for entry, score in scored:
            # Rough token count (1 token ≈ 4 chars)
            entry_tokens = len(entry['value']) // 4
            
            if total_tokens + entry_tokens <= max_tokens:
                selected.append(entry)
                total_tokens += entry_tokens
            else:
                break
        
        logger.info(f"Retrieved {len(selected)} relevant memories ({total_tokens} tokens)")
        return selected[:max_results]
    
    def search_entries(self, query: str) -> List[dict]:
        """Simple text search in memories"""
        entries = self.get_all_entries()
        query_lower = query.lower()
        
        results = [
            e for e in entries
            if query_lower in e['value'].lower() or query_lower in e['key'].lower()
        ]
        
        return results
    
    def get_by_category(self, category: str) -> List[dict]:
        """Filter by category"""
        entries = self.get_all_entries()
        return [e for e in entries if e['category'] == category]
    
    def clear_all(self) -> bool:
        """Nuclear option: delete all memories"""
        self._save({
            "entries": [],
            "metadata": {
                "created": datetime.now().isoformat(),
                "total_entries": 0,
                "last_cleared": datetime.now().isoformat()
            }
        })
        logger.warning("ALL MEMORIES CLEARED")
        return True
    
    def detect_conflicts(self) -> List[tuple]:
        """Detect conflicting memories (same key, different values)"""
        entries = self.get_all_entries()
        conflicts = []
        
        for i, e1 in enumerate(entries):
            for e2 in entries[i+1:]:
                if (e1['category'] == e2['category'] and 
                    e1['key'] == e2['key'] and 
                    e1['value'] != e2['value']):
                    conflicts.append((e1, e2))
        
        if conflicts:
            logger.warning(f"Found {len(conflicts)} conflicting memories")
        
        return conflicts


# Global instance
profile = ProfileManager()
