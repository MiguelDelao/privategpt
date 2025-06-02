"""
Embedding service using sentence-transformers BGE model
"""

import logging
from typing import List, Union
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
import os

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using BGE model"""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """
        Initialize the embedding service
        
        Args:
            model_name: The sentence-transformers model to use
        """
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    async def initialize(self):
        """Initialize the embedding model"""
        try:
            logger.info(f"🔄 Loading embedding model: {self.model_name}")
            
            # Load the model
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            
            # Set to evaluation mode
            self.model.eval()
            
            logger.info(f"✅ Embedding model loaded on {self.device}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of float values representing the embedding
        """
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        try:
            # Generate embedding
            with torch.no_grad():
                embedding = self.model.encode(
                    text,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            raise
    
    async def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embeddings as lists of floats
        """
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        try:
            embeddings = []
            
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                with torch.no_grad():
                    batch_embeddings = self.model.encode(
                        batch,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        batch_size=min(batch_size, len(batch))
                    )
                
                # Convert to list of lists
                embeddings.extend([emb.tolist() for emb in batch_embeddings])
            
            logger.info(f"✅ Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings: {e}")
            raise
    
    async def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Get embeddings
            embedding1 = await self.embed_text(text1)
            embedding2 = await self.embed_text(text2)
            
            # Convert to numpy arrays
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)
            
            # Compute cosine similarity
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"❌ Failed to compute similarity: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        return self.model.get_sentence_embedding_dimension()
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "dimension": self.get_embedding_dimension() if self.model else None,
            "max_seq_length": self.model.max_seq_length if self.model else None
        } 