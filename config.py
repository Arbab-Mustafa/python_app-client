"""
Production configuration for Texas School Psychology Assistant
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Production configuration class"""
    
    # Application Settings
    APP_NAME = "Texas School Psychology Assistant"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL_DEFAULT = "gpt-4o-mini"
    OPENAI_TEMPERATURE = 0
    
    # Embeddings Configuration (Lightweight TF-IDF)
    EMBEDDINGS_MODEL = "tfidf-lightweight"
    EMBEDDINGS_DEVICE = "cpu"
    
    # Vector Store Configuration
    VECTOR_STORE_PATH = "static_embeddings/faiss_index"
    CHUNKS_PATH = "static_embeddings/text_chunks.pkl"
    METADATA_PATH = "static_embeddings/metadata.json"
    
    # Search Configuration
    SEARCH_K = 30
    SEARCH_SCORE_THRESHOLD = 0.42
    
    # Text Processing
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Security
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    SESSION_TIMEOUT = 3600  # 1 hour
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # GCP Configuration
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    GCP_REGION = os.getenv("GCP_REGION", "us-central1")

    # Google Cloud Storage Configuration for Embeddings
    GCS_EMBEDDINGS_BUCKET = os.getenv("GCS_EMBEDDINGS_BUCKET", "texas-school-psychology-embeddings")
    GCS_USE_STORAGE = os.getenv("GCS_USE_STORAGE", "true").lower() == "true"
    
    # Production Settings
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_FILES_PER_UPLOAD = 10
    ALLOWED_FILE_TYPES = ['.pdf']
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required_vars = [
            "OPENAI_API_KEY",
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

# Production configuration instance
config = Config() 