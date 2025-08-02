#!/usr/bin/env python3
"""
Admin setup utility for Texas School Psychology Assistant
Handles PDF processing and embeddings creation for both local and GCP deployment
"""

import os
import sys
import argparse
import logging
import pickle
import json
from pathlib import Path
from datetime import datetime
from pypdf import PdfReader
from lightweight_vectorstore import LightweightVectorStore, from_texts
from lightweight_text_splitter import CharacterTextSplitter
from config import config

# Import GCS storage if enabled
gcs_storage = None
if config.GCS_USE_STORAGE:
    try:
        from gcs_storage import GCSStorage
        gcs_storage = GCSStorage()
        logger = logging.getLogger(__name__)
        logger.info("GCS Storage enabled for admin setup")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"GCS Storage initialization failed: {e}. Falling back to local storage.")
        gcs_storage = None
else:
    logger = logging.getLogger(__name__)
    logger.info("Using local storage for admin setup")

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}")
        return ""

def create_text_chunks(text):
    """Create text chunks for processing"""
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP
    )
    return text_splitter.split_text(text)

def create_embeddings(pdf_directory):
    """Create embeddings from PDF files in directory"""
    try:
        # Create embeddings directory for local storage
        os.makedirs("static_embeddings", exist_ok=True)
        
        # Find all PDF files
        pdf_files = list(Path(pdf_directory).glob("*.pdf"))
        if not pdf_files:
            logger.error(f"No PDF files found in {pdf_directory}")
            return False
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        # Extract text from all PDFs
        all_text = ""
        processed_files = []
        
        for pdf_file in pdf_files:
            logger.info(f"Processing {pdf_file.name}")
            text = extract_text_from_pdf(pdf_file)
            if text.strip():
                all_text += f"\n\n--- {pdf_file.name} ---\n\n{text}"
                processed_files.append(pdf_file.name)
            else:
                logger.warning(f"No text extracted from {pdf_file.name}")
        
        if not all_text.strip():
            logger.error("No text extracted from any PDF files")
            return False
        
        # Create chunks
        logger.info("Creating text chunks...")
        text_chunks = create_text_chunks(all_text)
        logger.info(f"Created {len(text_chunks)} chunks")
        
        # Create lightweight vectorstore
        logger.info("Creating lightweight vectorstore...")
        vectorstore = from_texts(texts=text_chunks)
        vectorstore.fit()
        
        # Save to local storage (always as backup)
        logger.info("Saving embeddings to local storage...")
        vectorstore.save_local(config.VECTOR_STORE_PATH)
        
        # Save chunks locally
        with open(config.CHUNKS_PATH, 'wb') as f:
            pickle.dump(text_chunks, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Save metadata locally
        metadata = {
            "created_at": datetime.now().isoformat(),
            "num_chunks": len(text_chunks),
            "num_pdfs": len(processed_files),
            "pdf_files": processed_files,
            "embedding_model": "lightweight_tfidf",
            "chunk_size": config.CHUNK_SIZE,
            "chunk_overlap": config.CHUNK_OVERLAP,
            "storage_type": "local_and_gcs" if gcs_storage and config.GCS_USE_STORAGE else "local_only"
        }
        
        with open(config.METADATA_PATH, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save to GCS if enabled
        if gcs_storage and config.GCS_USE_STORAGE:
            logger.info("Saving embeddings to Google Cloud Storage...")
            gcs_success = gcs_storage.save_embeddings(vectorstore, text_chunks, metadata)
            if gcs_success:
                logger.info("✅ Embeddings saved to both local storage and GCS")
            else:
                logger.warning("⚠️ Failed to save to GCS, but local storage is available")
        else:
            logger.info("✅ Embeddings saved to local storage only")
        
        logger.info("✅ Knowledge base created successfully!")
        logger.info(f"📊 Statistics:")
        logger.info(f"   - PDF files: {len(processed_files)}")
        logger.info(f"   - Text chunks: {len(text_chunks)}")
        logger.info(f"   - Local storage: {config.VECTOR_STORE_PATH}")
        if gcs_storage and config.GCS_USE_STORAGE:
            logger.info(f"   - GCS storage: {config.GCS_EMBEDDINGS_BUCKET}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        return False

def update_embeddings(pdf_directory):
    """Update existing embeddings with new PDFs"""
    logger.info("Updating knowledge base...")
    return create_embeddings(pdf_directory)

def show_status():
    """Show current knowledge base status"""
    try:
        # Check local storage
        local_metadata = None
        if os.path.exists(config.METADATA_PATH):
            with open(config.METADATA_PATH, 'r') as f:
                local_metadata = json.load(f)
        
        # Check GCS storage if enabled
        gcs_metadata = None
        if gcs_storage and config.GCS_USE_STORAGE:
            gcs_metadata = gcs_storage.get_embeddings_info()
        
        print("📚 Knowledge Base Status:")
        
        if local_metadata:
            print(f"   📁 Local Storage:")
            print(f"      Created: {local_metadata.get('created_at', 'Unknown')}")
            print(f"      PDF files: {local_metadata.get('num_pdfs', 0)}")
            print(f"      Text chunks: {local_metadata.get('num_chunks', 0)}")
            print(f"      Embedding model: {local_metadata.get('embedding_model', 'Unknown')}")
            
            if 'pdf_files' in local_metadata:
                print(f"      Processed PDF files:")
                for pdf in local_metadata['pdf_files']:
                    print(f"         - {pdf}")
        else:
            print("   📁 Local Storage: ❌ No knowledge base found")
        
        if gcs_storage and config.GCS_USE_STORAGE:
            if gcs_metadata:
                print(f"   ☁️  GCS Storage ({config.GCS_EMBEDDINGS_BUCKET}):")
                print(f"      Created: {gcs_metadata.get('created_at', 'Unknown')}")
                print(f"      PDF files: {gcs_metadata.get('num_pdfs', 0)}")
                print(f"      Text chunks: {gcs_metadata.get('num_chunks', 0)}")
                print(f"      Storage type: {gcs_metadata.get('storage_type', 'Unknown')}")
            else:
                print(f"   ☁️  GCS Storage ({config.GCS_EMBEDDINGS_BUCKET}): ❌ No knowledge base found")
        
        if not local_metadata and not gcs_metadata:
            print("❌ No knowledge base found in any storage. Run 'create' command first.")
            
    except Exception as e:
        logger.error(f"Error reading status: {e}")

def validate_setup():
    """Validate the current setup"""
    try:
        # Check required files
        required_files = [
            config.VECTOR_STORE_PATH,
            config.CHUNKS_PATH,
            config.METADATA_PATH
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False
        
        # Validate configuration
        config.validate()
        
        print("✅ Setup validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Setup validation failed: {e}")
        return False

def main():
    """Main admin utility function"""
    parser = argparse.ArgumentParser(
        description="Admin utility for Texas School Psychology Assistant"
    )
    parser.add_argument(
        'command',
        choices=['create', 'update', 'status', 'validate'],
        help='Command to execute'
    )
    parser.add_argument(
        '--pdf-dir',
        default='pdfs',
        help='Directory containing PDF files (default: pdfs)'
    )
    
    args = parser.parse_args()
    
    print(f"🔧 Texas School Psychology Assistant - Admin Utility")
    print(f"Command: {args.command}")
    
    if args.command == 'create':
        if not os.path.exists(args.pdf_dir):
            print(f"❌ PDF directory '{args.pdf_dir}' not found")
            sys.exit(1)
        success = create_embeddings(args.pdf_dir)
        sys.exit(0 if success else 1)
        
    elif args.command == 'update':
        if not os.path.exists(args.pdf_dir):
            print(f"❌ PDF directory '{args.pdf_dir}' not found")
            sys.exit(1)
        success = update_embeddings(args.pdf_dir)
        sys.exit(0 if success else 1)
        
    elif args.command == 'status':
        show_status()
        
    elif args.command == 'validate':
        success = validate_setup()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 