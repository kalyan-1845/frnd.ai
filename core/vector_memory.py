import os
import chromadb
from typing import List, Dict, Any, Optional
from core.logger import log_event, log_error

# Define absolute base path for database storage to ensure portability across execution contexts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data", "memory_db")

class VectorMemory:
    """
    Manages semantic long-term memory retrieval and storage for the assistant
    using a persistent local ChromaDB vector database.
    """
    def __init__(self) -> None:
        self.collection: Optional[chromadb.Collection] = None
        try:
            os.makedirs(DB_DIR, exist_ok=True)
            self.client = chromadb.PersistentClient(path=DB_DIR)
            self.collection = self.client.get_or_create_collection(name="long_term_memory")
            log_event("VectorMemory", f"Persistent ChromaDB cluster successfully established at: {DB_DIR}")
        except Exception as e:
            log_error("VectorMemoryInit", e)

    def save_memory(self, text: str, role: str) -> None:
        """
        Saves a conversation segment with metadata roles to the vector database.
        
        Args:
            text (str): The conversation segment content to persist.
            role (str): The role associated with the message (e.g., 'user', 'assistant').
        """
        if not self.collection or not text.strip():
            return
            
        try:
            # Generate deterministic unique identifier using current collection count metrics
            count = self.collection.count()
            self.collection.add(
                documents=[text],
                metadatas=[{"role": role}],
                ids=[f"mem_{count}_{role}"]
            )
            log_event("VectorMemorySave", f"Stored memory segment 'mem_{count}_{role}' in ChromaDB.")
        except Exception as e:
            log_error("VectorMemorySave", e)

    def retrieve_relevant_memory(self, query: str, top_k: int = 3) -> str:
        """
        Queries the vector index to retrieve semantically related memories.
        
        Args:
            query (str): The search query to compare against the stored documents.
            top_k (int): Maximum number of semantic matches to return.
            
        Returns:
            str: Pipe-separated string of matching memory records or empty string.
        """
        if not self.collection or not query.strip():
            return ""
            
        try:
            total_elements = self.collection.count()
            if total_elements == 0:
                return ""
                
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, total_elements)
            )
            
            if results and results.get('documents') and results['documents'][0]:
                docs: List[str] = results['documents'][0]
                metas: List[Dict[str, Any]] = results['metadatas'][0]
                
                context_parts: List[str] = []
                for doc, meta in zip(docs, metas):
                    role_lbl = meta.get('role', 'unknown').capitalize()
                    context_parts.append(f"{role_lbl}: {doc}")
                return " | ".join(context_parts)
                
            return ""
        except Exception as e:
            log_error("VectorMemoryRetrieve", e)
            return ""

# Expose global instance for application-wide session tracking
memory_db = VectorMemory()
