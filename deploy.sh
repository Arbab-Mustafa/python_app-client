#!/bin/bash

# 🚀 Texas School Psychology Assistant - Deployment Script
# This script handles deployment for both local and GCP environments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME="txpsybot"
BUCKET_NAME="txpsybot-pdfs-${PROJECT_ID}"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python &> /dev/null; then
        log_error "Python is not installed"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip &> /dev/null; then
        log_error "pip is not installed"
        exit 1
    fi
    
    # Check gcloud (for GCP deployment)
    if [[ "$1" == "gcp" ]] && ! command -v gcloud &> /dev/null; then
        log_error "Google Cloud SDK is not installed"
        exit 1
    fi
    
    log_success "Dependencies check passed"
}

setup_local_environment() {
    log_info "Setting up local environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    pip install -r Requirements.txt
    
    log_success "Local environment setup completed"
}

upload_files_local() {
    log_info "Uploading files locally..."
    
    # Check if files exist
    if [ ! -d "pdfs" ] || [ -z "$(ls -A pdfs 2>/dev/null)" ]; then
        log_warning "No PDF files found in pdfs directory"
        return
    fi
    
    # Upload files using backend admin
    python backend_admin.py upload-multiple --files pdfs/*.pdf
    
    # Create knowledge base
    log_info "Creating knowledge base..."
    python admin_setup.py create --pdf-dir pdfs
    
    log_success "Local file upload completed"
}

deploy_local() {
    log_info "Deploying locally..."
    
    # Check if virtual environment is activated
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        log_warning "Virtual environment not activated, activating now..."
        source venv/bin/activate
    fi
    
    # Start Streamlit application
    log_info "Starting Streamlit application..."
    streamlit run app.py --server.port 8501 --server.address 0.0.0.0
}

setup_gcp_environment() {
    log_info "Setting up GCP environment..."
    
    # Set project
    gcloud config set project $PROJECT_ID
    
    # Enable required APIs
    log_info "Enabling required APIs..."
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    gcloud services enable storage.googleapis.com
    gcloud services enable compute.googleapis.com
    
    # Create storage bucket if it doesn't exist
    if ! gsutil ls -b gs://$BUCKET_NAME &>/dev/null; then
        log_info "Creating Cloud Storage bucket..."
        gsutil mb gs://$BUCKET_NAME
        gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME
    fi
    
    log_success "GCP environment setup completed"
}

upload_files_gcp() {
    log_info "Uploading files to GCP..."
    
    # Check if files exist
    if [ ! -d "pdfs" ] || [ -z "$(ls -A pdfs 2>/dev/null)" ]; then
        log_warning "No PDF files found in pdfs directory"
        return
    fi
    
    # Upload files to Cloud Storage
    log_info "Uploading PDFs to Cloud Storage..."
    gsutil -m cp pdfs/*.pdf gs://$BUCKET_NAME/
    
    # Download files locally for processing
    log_info "Downloading files for processing..."
    gsutil -m cp gs://$BUCKET_NAME/*.pdf ./pdfs/
    
    # Create knowledge base
    log_info "Creating knowledge base..."
    python admin_setup.py create --pdf-dir pdfs
    
    log_success "GCP file upload completed"
}

build_and_deploy_gcp() {
    log_info "Building and deploying to GCP..."
    
    # Build Docker image
    log_info "Building Docker image..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME
    
    # Deploy to Cloud Run
    log_info "Deploying to Cloud Run..."
    gcloud run deploy $SERVICE_NAME \
        --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 1 \
        --timeout 300 \
        --concurrency 80 \
        --max-instances 10 \
        --set-env-vars "OPENAI_API_KEY=$OPENAI_API_KEY,ADMIN_PASSWORD=$ADMIN_PASSWORD"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    log_success "Deployment completed! Service URL: $SERVICE_URL"
}

validate_deployment() {
    log_info "Validating deployment..."
    
    # Run production tests
    python test_production.py
    
    log_success "Deployment validation completed"
}

show_help() {
    echo "🚀 Texas School Psychology Assistant - Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  local-setup     Setup local development environment"
    echo "  local-upload    Upload files locally"
    echo "  local-deploy    Deploy locally"
    echo "  gcp-setup       Setup GCP environment"
    echo "  gcp-upload      Upload files to GCP"
    echo "  gcp-deploy      Deploy to GCP"
    echo "  full-local      Complete local setup and deployment"
    echo "  full-gcp        Complete GCP setup and deployment"
    echo "  validate        Validate deployment"
    echo "  help            Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GCP_PROJECT_ID  Google Cloud Project ID"
    echo "  GCP_REGION      Google Cloud Region (default: us-central1)"
    echo "  OPENAI_API_KEY  OpenAI API Key"
    echo "  ADMIN_PASSWORD  Admin password for the application"
    echo ""
    echo "Examples:"
    echo "  $0 full-local"
    echo "  $0 full-gcp"
    echo "  GCP_PROJECT_ID=my-project $0 gcp-deploy"
}

# Main script
case "${1:-help}" in
    "local-setup")
        check_dependencies
        setup_local_environment
        ;;
    "local-upload")
        upload_files_local
        ;;
    "local-deploy")
        deploy_local
        ;;
    "gcp-setup")
        check_dependencies gcp
        setup_gcp_environment
        ;;
    "gcp-upload")
        upload_files_gcp
        ;;
    "gcp-deploy")
        check_dependencies gcp
        build_and_deploy_gcp
        ;;
    "full-local")
        check_dependencies
        setup_local_environment
        upload_files_local
        validate_deployment
        log_success "Local deployment completed! Run 'streamlit run app.py' to start the application."
        ;;
    "full-gcp")
        check_dependencies gcp
        setup_gcp_environment
        upload_files_gcp
        build_and_deploy_gcp
        validate_deployment
        ;;
    "validate")
        validate_deployment
        ;;
    "help"|*)
        show_help
        ;;
esac 