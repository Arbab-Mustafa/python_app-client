#!/usr/bin/env python3
"""
Google Cloud Storage helper for Texas School Psychology Assistant
Handles embeddings storage and retrieval for GCP deployment
"""

import os
import pickle
import json
import tempfile
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    print("Warning: Google Cloud Storage not available. Install google-cloud-storage for GCS support.")
from config import config

logger = logging.getLogger(__name__)

class GCSStorage:
    """Google Cloud Storage helper for embeddings management"""
    
    def __init__(self):
        """Initialize GCS client and bucket"""
        if not GCS_AVAILABLE:
            raise ImportError("Google Cloud Storage not available. Install google-cloud-storage package.")
        
        try:
            # Use default credentials (service account in Cloud Run)
            self.client = storage.Client(project=config.GCP_PROJECT_ID)
            self.bucket = self.client.bucket(config.GCS_EMBEDDINGS_BUCKET)
            logger.info(f"GCS Storage initialized for bucket: {config.GCS_EMBEDDINGS_BUCKET}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS Storage: {e}")
            raise
    
    def save_embeddings(self, vectorstore, text_chunks: list, metadata: dict) -> bool:
        """
        Save embeddings, chunks, and metadata to GCS
        
        Args:
            vectorstore: FAISS vectorstore object
            text_chunks: List of text chunks
            metadata: Metadata dictionary
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Saving embeddings to Google Cloud Storage...")
            
            # Create temporary directory for files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save FAISS index
                faiss_path = os.path.join(temp_dir, "faiss_index")
                vectorstore.save_local(faiss_path)
                
                # Upload FAISS index
                faiss_blob = self.bucket.blob("embeddings/faiss_index")
                for root, dirs, files in os.walk(faiss_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        blob_path = f"embeddings/faiss_index/{os.path.relpath(file_path, faiss_path)}"
                        blob = self.bucket.blob(blob_path)
                        blob.upload_from_filename(file_path)
                
                # Save and upload text chunks
                chunks_path = os.path.join(temp_dir, "text_chunks.pkl")
                with open(chunks_path, 'wb') as f:
                    pickle.dump(text_chunks, f, protocol=pickle.HIGHEST_PROTOCOL)
                
                chunks_blob = self.bucket.blob("embeddings/text_chunks.pkl")
                chunks_blob.upload_from_filename(chunks_path)
                
                # Save and upload metadata
                metadata_path = os.path.join(temp_dir, "metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                metadata_blob = self.bucket.blob("embeddings/metadata.json")
                metadata_blob.upload_from_filename(metadata_path)
            
            logger.info("✅ Embeddings saved to GCS successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving embeddings to GCS: {e}")
            return False
    
    def load_embeddings(self) -> Tuple[Optional[Any], Optional[list], Optional[dict]]:
        """
        Load embeddings, chunks, and metadata from GCS
        
        Returns:
            Tuple: (vectorstore, text_chunks, metadata) or (None, None, None) if failed
        """
        try:
            logger.info("Loading embeddings from Google Cloud Storage...")
            
            # Check if embeddings exist
            metadata_blob = self.bucket.blob("embeddings/metadata.json")
            if not metadata_blob.exists():
                logger.warning("No embeddings found in GCS")
                return None, None, None
            
            # Create temporary directory for files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download metadata
                metadata_path = os.path.join(temp_dir, "metadata.json")
                metadata_blob.download_to_filename(metadata_path)
                
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Download text chunks
                chunks_path = os.path.join(temp_dir, "text_chunks.pkl")
                chunks_blob = self.bucket.blob("embeddings/text_chunks.pkl")
                chunks_blob.download_to_filename(chunks_path)
                
                with open(chunks_path, 'rb') as f:
                    text_chunks = pickle.load(f)
                
                # Download FAISS index
                faiss_path = os.path.join(temp_dir, "faiss_index")
                os.makedirs(faiss_path, exist_ok=True)
                
                # List all files in faiss_index directory
                faiss_prefix = "embeddings/faiss_index/"
                blobs = self.client.list_blobs(self.bucket, prefix=faiss_prefix)
                
                for blob in blobs:
                    if blob.name != faiss_prefix:  # Skip the directory itself
                        relative_path = blob.name.replace(faiss_prefix, "")
                        local_path = os.path.join(faiss_path, relative_path)
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        blob.download_to_filename(local_path)
                
                # Load lightweight vectorstore
                from lightweight_vectorstore import LightweightVectorStore
                
                vectorstore = LightweightVectorStore.load_local(faiss_path)
            
            logger.info(f"✅ Loaded embeddings from GCS: {len(text_chunks)} chunks")
            return vectorstore, text_chunks, metadata
            
        except Exception as e:
            logger.error(f"❌ Error loading embeddings from GCS: {e}")
            return None, None, None
    
    def embeddings_exist(self) -> bool:
        """Check if embeddings exist in GCS"""
        try:
            metadata_blob = self.bucket.blob("embeddings/metadata.json")
            return metadata_blob.exists()
        except Exception as e:
            logger.error(f"Error checking embeddings existence: {e}")
            return False
    
    def get_embeddings_info(self) -> Optional[dict]:
        """Get information about stored embeddings"""
        try:
            metadata_blob = self.bucket.blob("embeddings/metadata.json")
            if not metadata_blob.exists():
                return None
            
            metadata_blob.download_to_filename("/tmp/metadata.json")
            with open("/tmp/metadata.json", 'r') as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting embeddings info: {e}")
            return None
    
    def delete_embeddings(self) -> bool:
        """Delete all embeddings from GCS"""
        try:
            logger.info("Deleting embeddings from Google Cloud Storage...")
            
            # List all embeddings files
            blobs = self.client.list_blobs(self.bucket, prefix="embeddings/")
            
            # Delete each blob
            for blob in blobs:
                blob.delete()
            
            logger.info("✅ Embeddings deleted from GCS successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting embeddings from GCS: {e}")
            return False 