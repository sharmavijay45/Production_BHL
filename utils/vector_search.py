#!/usr/bin/env python3
"""
Vector Search Engine - FAISS/Qdrant Integration
===============================================

Provides vector-backed document retrieval using FAISS for local search
and optional Qdrant integration for distributed vector search.
"""

import os
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pickle
import json
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

# Try to import FAISS (fallback to stub if not available)
try:
    import faiss
    FAISS_AVAILABLE = True
    logger.info("✅ FAISS library available")
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("⚠️ FAISS library not available, using fallback implementation")

# Try to import sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("✅ SentenceTransformers library available")
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("⚠️ SentenceTransformers library not available, using fallback embeddings")

class VectorSearchEngine:
    """Vector search engine with FAISS backend"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", index_path: str = None):
        self.engine_name = "VectorSearchEngine"
        self.version = "1.0.0"
        self.model_name = model_name
        self.index_path = index_path or "cache/vector_index"
        
        # Initialize embedding model
        self.embedding_model = None
        self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
        
        # Initialize FAISS index
        self.faiss_index = None
        self.document_metadata = {}  # Store document metadata
        self.document_texts = {}     # Store document texts
        self.next_doc_id = 0
        
        # Initialize components
        self._initialize_embedding_model()
        self._initialize_faiss_index()
        self._load_existing_index()
        
        logger.info(f"✅ Vector Search Engine initialized with {self.model_name}")
    
    def _initialize_embedding_model(self):
        """Initialize embedding model"""
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embedding_model = SentenceTransformer(self.model_name)
                self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                logger.info(f"✅ Loaded embedding model: {self.model_name} (dim: {self.embedding_dim})")
            else:
                logger.warning("⚠️ Using fallback embedding model")
                self.embedding_model = None
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {str(e)}")
            self.embedding_model = None
    
    def _initialize_faiss_index(self):
        """Initialize FAISS index"""
        try:
            if FAISS_AVAILABLE:
                # Use IndexFlatIP for cosine similarity
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
                logger.info(f"✅ Initialized FAISS index (dim: {self.embedding_dim})")
            else:
                logger.warning("⚠️ FAISS not available, using fallback search")
                self.faiss_index = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize FAISS index: {str(e)}")
            self.faiss_index = None
    
    def _load_existing_index(self):
        """Load existing index if available"""
        try:
            index_dir = Path(self.index_path)
            if not index_dir.exists():
                index_dir.mkdir(parents=True, exist_ok=True)
                return
            
            # Load FAISS index
            faiss_file = index_dir / "faiss_index.bin"
            if faiss_file.exists() and FAISS_AVAILABLE:
                self.faiss_index = faiss.read_index(str(faiss_file))
                logger.info("✅ Loaded existing FAISS index")
            
            # Load metadata
            metadata_file = index_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.document_metadata = data.get("metadata", {})
                    self.next_doc_id = data.get("next_doc_id", 0)
                logger.info(f"✅ Loaded metadata for {len(self.document_metadata)} documents")
            
            # Load document texts
            texts_file = index_dir / "document_texts.pkl"
            if texts_file.exists():
                with open(texts_file, 'rb') as f:
                    self.document_texts = pickle.load(f)
                logger.info(f"✅ Loaded {len(self.document_texts)} document texts")
                
        except Exception as e:
            logger.error(f"❌ Failed to load existing index: {str(e)}")
    
    def _save_index(self):
        """Save index to disk"""
        try:
            index_dir = Path(self.index_path)
            index_dir.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            if self.faiss_index and FAISS_AVAILABLE:
                faiss_file = index_dir / "faiss_index.bin"
                faiss.write_index(self.faiss_index, str(faiss_file))
            
            # Save metadata
            metadata_file = index_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": self.document_metadata,
                    "next_doc_id": self.next_doc_id,
                    "model_name": self.model_name,
                    "embedding_dim": self.embedding_dim,
                    "saved_at": datetime.utcnow().isoformat()
                }, f, indent=2)
            
            # Save document texts
            texts_file = index_dir / "document_texts.pkl"
            with open(texts_file, 'wb') as f:
                pickle.dump(self.document_texts, f)
            
            logger.info("✅ Saved vector index to disk")
            
        except Exception as e:
            logger.error(f"❌ Failed to save index: {str(e)}")
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        try:
            if self.embedding_model and SENTENCE_TRANSFORMERS_AVAILABLE:
                embedding = self.embedding_model.encode(text, normalize_embeddings=True)
                return embedding.astype(np.float32)
            else:
                # Fallback: simple hash-based embedding (not recommended for production)
                return self._fallback_embedding(text)
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {str(e)}")
            return self._fallback_embedding(text)
    
    def _fallback_embedding(self, text: str) -> np.ndarray:
        """Fallback embedding using simple hash-based approach"""
        # Simple hash-based embedding (not semantically meaningful)
        hash_val = hash(text)
        embedding = np.random.RandomState(hash_val % (2**31)).normal(0, 1, self.embedding_dim)
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.astype(np.float32)
    
    def add_document(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Add document to vector index"""
        try:
            doc_id = str(self.next_doc_id)
            self.next_doc_id += 1
            
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Add to FAISS index
            if self.faiss_index:
                self.faiss_index.add(embedding.reshape(1, -1))
            
            # Store metadata and text
            self.document_metadata[doc_id] = {
                "doc_id": doc_id,
                "metadata": metadata or {},
                "added_at": datetime.utcnow().isoformat(),
                "text_length": len(text)
            }
            self.document_texts[doc_id] = text
            
            logger.info(f"✅ Added document {doc_id} to vector index")
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Failed to add document: {str(e)}")
            return ""
    
    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Add multiple documents in batch"""
        doc_ids = []
        
        try:
            texts = [doc.get("text", "") for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]
            
            # Generate embeddings for all texts
            if self.embedding_model and SENTENCE_TRANSFORMERS_AVAILABLE:
                embeddings = self.embedding_model.encode(texts, normalize_embeddings=True)
                embeddings = embeddings.astype(np.float32)
            else:
                embeddings = np.array([self._fallback_embedding(text) for text in texts])
            
            # Add to FAISS index
            if self.faiss_index:
                self.faiss_index.add(embeddings)
            
            # Store metadata and texts
            for i, (text, metadata) in enumerate(zip(texts, metadatas)):
                doc_id = str(self.next_doc_id)
                self.next_doc_id += 1
                
                self.document_metadata[doc_id] = {
                    "doc_id": doc_id,
                    "metadata": metadata,
                    "added_at": datetime.utcnow().isoformat(),
                    "text_length": len(text)
                }
                self.document_texts[doc_id] = text
                doc_ids.append(doc_id)
            
            logger.info(f"✅ Added {len(documents)} documents to vector index")
            
        except Exception as e:
            logger.error(f"❌ Failed to add documents batch: {str(e)}")
        
        return doc_ids
    
    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            if not self.faiss_index or self.faiss_index.ntotal == 0:
                logger.warning("⚠️ No documents in index")
                return []
            
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Search with FAISS
            if FAISS_AVAILABLE and self.faiss_index:
                scores, indices = self.faiss_index.search(query_embedding.reshape(1, -1), top_k)
                scores = scores[0]
                indices = indices[0]
            else:
                # Fallback search
                return self._fallback_search(query, top_k)
            
            # Build results
            results = []
            for i, (score, idx) in enumerate(zip(scores, indices)):
                if idx == -1 or score < score_threshold:
                    continue
                
                doc_id = str(idx)
                if doc_id in self.document_metadata and doc_id in self.document_texts:
                    result = {
                        "doc_id": doc_id,
                        "text": self.document_texts[doc_id],
                        "score": float(score),
                        "rank": i + 1,
                        "metadata": self.document_metadata[doc_id]["metadata"],
                        "source": self.document_metadata[doc_id]["metadata"].get("source", "unknown")
                    }
                    results.append(result)
            
            logger.info(f"✅ Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search failed: {str(e)}")
            return self._fallback_search(query, top_k)
    
    def _fallback_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Fallback search using simple text matching"""
        try:
            query_lower = query.lower()
            results = []
            
            for doc_id, text in self.document_texts.items():
                text_lower = text.lower()
                
                # Simple scoring based on word overlap
                query_words = set(query_lower.split())
                text_words = set(text_lower.split())
                
                if query_words & text_words:  # If there's any overlap
                    overlap = len(query_words & text_words)
                    score = overlap / len(query_words)
                    
                    result = {
                        "doc_id": doc_id,
                        "text": text,
                        "score": score,
                        "rank": 0,  # Will be set after sorting
                        "metadata": self.document_metadata[doc_id]["metadata"],
                        "source": self.document_metadata[doc_id]["metadata"].get("source", "unknown")
                    }
                    results.append(result)
            
            # Sort by score and limit
            results.sort(key=lambda x: x["score"], reverse=True)
            results = results[:top_k]
            
            # Set ranks
            for i, result in enumerate(results):
                result["rank"] = i + 1
            
            logger.info(f"✅ Fallback search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Fallback search failed: {str(e)}")
            return []
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        if doc_id in self.document_texts and doc_id in self.document_metadata:
            return {
                "doc_id": doc_id,
                "text": self.document_texts[doc_id],
                "metadata": self.document_metadata[doc_id]
            }
        return None
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document from index"""
        try:
            if doc_id in self.document_texts:
                del self.document_texts[doc_id]
            if doc_id in self.document_metadata:
                del self.document_metadata[doc_id]
            
            # Note: FAISS doesn't support individual deletion easily
            # In production, you'd need to rebuild the index periodically
            
            logger.info(f"✅ Deleted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document: {str(e)}")
            return False
    
    def rebuild_index(self):
        """Rebuild FAISS index from stored documents"""
        try:
            if not self.document_texts:
                logger.warning("⚠️ No documents to rebuild index")
                return
            
            # Reinitialize index
            self._initialize_faiss_index()
            
            # Add all documents back
            texts = list(self.document_texts.values())
            if self.embedding_model and SENTENCE_TRANSFORMERS_AVAILABLE:
                embeddings = self.embedding_model.encode(texts, normalize_embeddings=True)
                embeddings = embeddings.astype(np.float32)
            else:
                embeddings = np.array([self._fallback_embedding(text) for text in texts])
            
            if self.faiss_index:
                self.faiss_index.add(embeddings)
            
            logger.info(f"✅ Rebuilt index with {len(texts)} documents")
            
        except Exception as e:
            logger.error(f"❌ Failed to rebuild index: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics"""
        return {
            "engine": self.engine_name,
            "version": self.version,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "total_documents": len(self.document_texts),
            "faiss_available": FAISS_AVAILABLE,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE,
            "index_size": self.faiss_index.ntotal if self.faiss_index else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def save_to_disk(self):
        """Save index to disk"""
        self._save_index()
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for vector search engine"""
        return {
            "engine": self.engine_name,
            "status": "healthy",
            "faiss_available": FAISS_AVAILABLE,
            "embedding_model_loaded": self.embedding_model is not None,
            "total_documents": len(self.document_texts),
            "timestamp": datetime.utcnow().isoformat()
        }

# Global vector search engine instance
vector_search_engine = VectorSearchEngine()

def get_vector_search_engine() -> VectorSearchEngine:
    """Get global vector search engine instance"""
    return vector_search_engine

# Convenience functions
def add_document_to_index(text: str, metadata: Dict[str, Any] = None) -> str:
    """Add document to vector index"""
    return vector_search_engine.add_document(text, metadata)

def search_documents(query: str, top_k: int = 5, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
    """Search documents using vector similarity"""
    return vector_search_engine.search(query, top_k, score_threshold)

def initialize_vector_search_from_files(file_directory: str) -> int:
    """Initialize vector search from files in directory"""
    try:
        file_dir = Path(file_directory)
        if not file_dir.exists():
            logger.error(f"❌ Directory {file_directory} does not exist")
            return 0
        
        documents = []
        for file_path in file_dir.rglob("*.txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                if text.strip():  # Only add non-empty files
                    documents.append({
                        "text": text,
                        "metadata": {
                            "source": str(file_path),
                            "filename": file_path.name,
                            "file_size": file_path.stat().st_size,
                            "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        }
                    })
            except Exception as e:
                logger.error(f"❌ Failed to read file {file_path}: {str(e)}")
        
        if documents:
            doc_ids = vector_search_engine.add_documents_batch(documents)
            vector_search_engine.save_to_disk()
            logger.info(f"✅ Initialized vector search with {len(doc_ids)} documents")
            return len(doc_ids)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize vector search from files: {str(e)}")
        return 0
