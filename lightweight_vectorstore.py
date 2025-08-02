"""
Lightweight Vector Store Implementation
Uses scikit-learn instead of FAISS for smaller footprint
"""

import os
import pickle
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class LightweightVectorStore:
    """Lightweight vector store using scikit-learn TF-IDF"""
    
    def __init__(self, texts: Optional[List[str]] = None, embedding_model=None):
        """
        Initialize vector store
        
        Args:
            texts: List of text chunks
            embedding_model: Embedding model (not used in this implementation)
        """
        self.texts = texts or []
        self.vectorizer = TfidfVectorizer(
            max_features=10000,  # Limit features for memory efficiency
            ngram_range=(1, 2),  # Use unigrams and bigrams
            stop_words='english',
            min_df=2,  # Minimum document frequency
            max_df=0.95  # Maximum document frequency
        )
        self.vectors = None
        self._fitted = False
        
        if texts:
            self.add_texts(texts)
    
    def add_texts(self, texts: List[str]) -> None:
        """Add texts to the vector store"""
        if not texts:
            return
            
        self.texts.extend(texts)
        self._fitted = False  # Need to refit
    
    def fit(self) -> None:
        """Fit the vectorizer and create vectors"""
        if not self.texts:
            logger.warning("No texts to fit")
            return
            
        try:
            self.vectors = self.vectorizer.fit_transform(self.texts)
            self._fitted = True
            logger.info(f"Fitted vectorizer with {len(self.texts)} texts")
        except Exception as e:
            logger.error(f"Error fitting vectorizer: {e}")
            raise
    
    def similarity_search(self, query: str, k: int = 4, score_threshold: float = 0.0) -> List[Tuple[str, float]]:
        """
        Search for similar texts
        
        Args:
            query: Search query
            k: Number of results to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of (text, score) tuples
        """
        if not self._fitted:
            self.fit()
        
        if not self._fitted or self.vectors is None:
            return []
        
        try:
            # Transform query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.vectors).flatten()
            
            # Get top k results above threshold
            results = []
            for i, score in enumerate(similarities):
                if score >= score_threshold:
                    results.append((self.texts[i], float(score)))
            
            # Sort by score and return top k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:k]
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    def save_local(self, path: str) -> None:
        """Save vector store to local directory"""
        try:
            os.makedirs(path, exist_ok=True)
            
            # Save vectorizer
            with open(os.path.join(path, 'vectorizer.pkl'), 'wb') as f:
                pickle.dump(self.vectorizer, f)
            
            # Save vectors
            with open(os.path.join(path, 'vectors.pkl'), 'wb') as f:
                pickle.dump(self.vectors, f)
            
            # Save texts
            with open(os.path.join(path, 'texts.pkl'), 'wb') as f:
                pickle.dump(self.texts, f)
            
            # Save metadata
            metadata = {
                'num_texts': len(self.texts),
                'vectorizer_type': 'tfidf',
                'fitted': self._fitted
            }
            with open(os.path.join(path, 'metadata.json'), 'w') as f:
                json.dump(metadata, f)
                
            logger.info(f"Saved vector store to {path}")
            
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            raise
    
    @classmethod
    def load_local(cls, path: str, embedding_model=None) -> 'LightweightVectorStore':
        """Load vector store from local directory"""
        try:
            # Load vectorizer
            with open(os.path.join(path, 'vectorizer.pkl'), 'rb') as f:
                vectorizer = pickle.load(f)
            
            # Load vectors
            with open(os.path.join(path, 'vectors.pkl'), 'rb') as f:
                vectors = pickle.load(f)
            
            # Load texts
            with open(os.path.join(path, 'texts.pkl'), 'rb') as f:
                texts = pickle.load(f)
            
            # Create instance
            instance = cls()
            instance.vectorizer = vectorizer
            instance.vectors = vectors
            instance.texts = texts
            instance._fitted = True
            
            logger.info(f"Loaded vector store from {path} with {len(texts)} texts")
            return instance
            
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            raise
    
    def as_retriever(self, search_type: str = "similarity", search_kwargs: Dict = None) -> 'LightweightRetriever':
        """Create a retriever interface"""
        if search_kwargs is None:
            search_kwargs = {}
        return LightweightRetriever(self, search_kwargs)


class LightweightRetriever:
    """Retriever interface for LightweightVectorStore"""
    
    def __init__(self, vectorstore: LightweightVectorStore, search_kwargs: Dict):
        self.vectorstore = vectorstore
        self.search_kwargs = search_kwargs
    
    def get_relevant_documents(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant documents for a query"""
        k = self.search_kwargs.get('k', 4)
        score_threshold = self.search_kwargs.get('score_threshold', 0.0)
        
        results = self.vectorstore.similarity_search(query, k, score_threshold)
        
        # Convert to document format
        documents = []
        for text, score in results:
            documents.append({
                'page_content': text,
                'metadata': {'score': score}
            })
        
        return documents


# Factory function for compatibility
def from_texts(texts: List[str], embedding=None, **kwargs) -> LightweightVectorStore:
    """Create vector store from texts (compatibility with FAISS interface)"""
    return LightweightVectorStore(texts, embedding) 