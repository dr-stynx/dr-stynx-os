"""
Mem0 integration for Dr. Stynx OS.
Provides long-term memory with semantic search and auto-extraction.
"""
import os
from typing import Optional, Dict, Any, List

from mem0 import Memory
from mem0.configs.base import MemoryConfig, EmbedderConfig, LlmConfig, VectorStoreConfig

# Persistent storage path
MEM0_DIR = os.path.expanduser("~/.dr-stynx-mem0")
os.makedirs(MEM0_DIR, exist_ok=True)

# Configure Mem0 with local embeddings and Chroma vector store
def create_memory_config() -> MemoryConfig:
    """Create a Mem0 config using fastembed (local) + Anthropic LLM (via DeepSeek)."""
    return MemoryConfig(
        embedder=EmbedderConfig(
            provider="fastembed",
            config={"model": "nomic-ai/nomic-embed-text-v1.5"}
        ),
        llm=LlmConfig(
            provider="anthropic",
            config={"api_key": os.environ.get("ANTHROPIC_AUTH_TOKEN", "")}
        ),
        vector_store=VectorStoreConfig(
            provider="chroma",
            config={"path": os.path.join(MEM0_DIR, "chroma")}
        ),
        history_db_path=os.path.join(MEM0_DIR, "history.db")
    )

# Global memory instance (initialized lazily)
_memory: Optional[Memory] = None

def get_memory() -> Memory:
    """Get or create the global Mem0 instance."""
    global _memory
    if _memory is None:
        _memory = Memory(config=create_memory_config())
    return _memory

def store_memory(text: str, category: str = "general", tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Store a memory with metadata.
    
    Args:
        text: The memory content
        category: Category for organization (e.g., "project", "debugging", "decision")
        tags: Optional tags for filtering
    """
    mem = get_memory()
    
    # Build metadata
    metadata = {"category": category}
    if tags:
        metadata["tags"] = tags
    
    # Store with user_id for scoping
    result = mem.add(
        text,
        user_id="dr-stynx",
        metadata=metadata,
        infer=False  # We handle extraction ourselves
    )
    return result

def search_memory(query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search memories by semantic similarity.
    
    Args:
        query: Search query
        limit: Max results to return
        category: Optional category filter
    """
    mem = get_memory()
    result = mem.search(query, filters={"user_id": "dr-stynx"}, limit=limit)
    results = result.get("results", [])
    
    # Filter by category if specified
    if category:
        filtered = []
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("category") == category:
                filtered.append(r)
        results = filtered
    
    return results

def list_memories(category: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    List all memories, optionally filtered by category.
    
    Args:
        category: Optional category filter
        limit: Max memories to return
    """
    mem = get_memory()
    all_result = mem.get_all(filters={"user_id": "dr-stynx"}, limit=limit)
    all_memories = all_result.get("results", [])
    
    if category:
        filtered = []
        for m in all_memories:
            meta = m.get("metadata", {})
            if meta.get("category") == category:
                filtered.append(m)
        return filtered
    
    return all_memories

def delete_memory(memory_id: str) -> bool:
    """Delete a memory by ID."""
    mem = get_memory()
    try:
        mem.delete(memory_id)
        return True
    except Exception:
        return False

def clear_all_memories() -> bool:
    """Clear all memories for dr-stynx."""
    mem = get_memory()
    mem.delete_all(user_id="dr-stynx")
    return True

def get_memory_stats() -> Dict[str, Any]:
    """Get statistics about stored memories."""
    mem = get_memory()
    all_result = mem.get_all(filters={"user_id": "dr-stynx"}, limit=1000)
    all_memories = all_result.get("results", [])
    
    # Count by category
    categories = {}
    for m in all_memories:
        cat = m.get("metadata", {}).get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "total_memories": len(all_memories),
        "by_category": categories,
        "storage_path": MEM0_DIR
    }
