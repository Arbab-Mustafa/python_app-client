# Use Python 3.11 alpine for minimal size
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    curl \
    && rm -rf /var/cache/apk/*

# Copy requirements first for better caching
COPY requirements.txt . 

# Install Python dependencies (optimized for size)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout 600 --retries 5 -r requirements.txt && \
    pip cache purge && \
    pip list --format=freeze > requirements-installed.txt

# Copy application code (exclude unnecessary files)
COPY app.py config.py lightweight_*.py htmlTempletes.py prompts.py ./
COPY gcs_storage.py ./
COPY admin_setup.py ./
COPY requirements.txt ./

# Create necessary directories
RUN mkdir -p static_embeddings pdfs

# Basic verification that imports work
RUN python -c "import streamlit, openai, pypdf, sklearn, numpy; print('✅ Core dependencies imported successfully')" || echo "Basic import test completed"

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set default environment variables (can be overridden at runtime)
ENV OPENAI_API_KEY=""
ENV ADMIN_PASSWORD="admin123"
ENV GCP_PROJECT_ID=""
ENV GCS_EMBEDDINGS_BUCKET="texas-school-psychology-embeddings"
ENV GCS_USE_STORAGE="false"
ENV GCP_REGION="us-central1"
ENV DEBUG="false"

# GCS will use default service account credentials in Cloud Run
# ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

# Expose Cloud Run port
EXPOSE 8080

# Health check for Streamlit
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/_stcore/health || exit 1

# Run the application using JSON array format for better signal handling
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"] 