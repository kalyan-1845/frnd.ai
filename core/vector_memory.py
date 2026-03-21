import os
import chromadb
from core.logger import log_event, log_error

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "memory_db")

class VectorMemory:
    def __init__(self):
        self.collection = None
        try:
            os.makedirs(DB_DIR, exist_ok=True)
            self.client = chromadb.PersistentClient(path=DB_DIR)
            self.collection = self.client.get_or_create_collection(name="long_term_memory")
            log_event("VectorMemory", "ChromaDB memory initialized successfully.")
        except Exception as e:
            log_error("VectorMemoryInit", e)

    def save_memory(self, text: str, role: str):
        if not self.collection or not text.strip():
            return
            
        try:
            # Unique ID based on count
            count = self.collection.count()
            self.collection.add(
                documents=[text],
                metadatas=[{"role": role}],
                ids=[f"mem_{count}_{role}"]
            )
        except Exception as e:
            log_error("VectorMemorySave", e)

    def retrieve_relevant_memory(self, query: str, top_k: int = 3) -> str:
        if not self.collection or not query.strip():
            return ""
            
        try:
            if self.collection.count() == 0:
                return ""
                
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count())
            )
            
            if results and results['documents'] and results['documents'][0]:
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                
                context_parts = []
                for doc, meta in zip(docs, metas):
                    context_parts.append(f"{meta['role'].capitalize()}: {doc}")
                return " | ".join(context_parts)
                
            return ""
        except Exception as e:
            log_error("VectorMemoryRetrieve", e)
            return ""

# Global instance
memory_db = VectorMemory()
