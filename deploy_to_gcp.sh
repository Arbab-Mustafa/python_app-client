#!/bin/bash

# GCP Deployment Script for Lightweight Texas School Psychology Assistant
# This script deploys the lightweight version to Google Cloud Platform

set -e  # Exit on any error

echo "🚀 Deploying Lightweight Texas School Psychology Assistant to GCP"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-""}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME="texas-school-psychology-assistant"
IMAGE_NAME="texas-school-psychology-assistant:lightweight"
GCR_IMAGE_NAME=""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_error "You are not authenticated with gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Get project ID if not provided
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        print_error "No project ID specified. Please set GCP_PROJECT_ID environment variable or run 'gcloud config set project YOUR_PROJECT_ID'"
        exit 1
    fi
fi

print_status "Using project: $PROJECT_ID"
print_status "Using region: $REGION"

# Set the GCR image name
GCR_IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME:lightweight"

# Build the Docker image locally
echo "🔨 Building Docker image..."
docker build -t $IMAGE_NAME .

if [ $? -eq 0 ]; then
    print_status "Docker image built successfully"
else
    print_error "Docker build failed"
    exit 1
fi

# Test the image locally
echo "🧪 Testing Docker image locally..."
docker run --rm $IMAGE_NAME python quick_test.py

if [ $? -eq 0 ]; then
    print_status "Local test passed"
else
    print_error "Local test failed"
    exit 1
fi

# Configure Docker to use gcloud as a credential helper
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker

# Tag the image for GCR
echo "🏷️  Tagging image for GCR..."
docker tag $IMAGE_NAME $GCR_IMAGE_NAME

# Push the image to GCR
echo "📤 Pushing image to Google Container Registry..."
docker push $GCR_IMAGE_NAME

if [ $? -eq 0 ]; then
    print_status "Image pushed to GCR successfully"
else
    print_error "Failed to push image to GCR"
    exit 1
fi

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."

# Check if service already exists
if gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(metadata.name)" 2>/dev/null | grep -q $SERVICE_NAME; then
    print_status "Updating existing Cloud Run service..."
    gcloud run deploy $SERVICE_NAME \
        --image=$GCR_IMAGE_NAME \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --memory=1Gi \
        --cpu=1 \
        --max-instances=5 \
        --set-env-vars="OPENAI_API_KEY=${OPENAI_API_KEY}" \
        --set-env-vars="GCS_USE_STORAGE=${GCS_USE_STORAGE:-false}" \
        --set-env-vars="DEBUG=${DEBUG:-false}"
else
    print_status "Creating new Cloud Run service..."
    gcloud run deploy $SERVICE_NAME \
        --image=$GCR_IMAGE_NAME \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --memory=1Gi \
        --cpu=1 \
        --max-instances=5 \
        --set-env-vars="OPENAI_API_KEY=${OPENAI_API_KEY}" \
        --set-env-vars="GCS_USE_STORAGE=${GCS_USE_STORAGE:-false}" \
        --set-env-vars="DEBUG=${DEBUG:-false}"
fi

if [ $? -eq 0 ]; then
    print_status "Cloud Run service deployed successfully"
else
    print_error "Failed to deploy to Cloud Run"
    exit 1
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

print_status "Service deployed successfully!"
print_status "Service URL: $SERVICE_URL"

# Show service information
echo ""
echo "📋 Service Information:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="table(metadata.name,status.url,spec.template.spec.containers[0].resources.limits.memory,spec.template.spec.containers[0].resources.limits.cpu)"

# Test the deployed service
echo ""
echo "🧪 Testing deployed service..."
if curl -f "$SERVICE_URL/_stcore/health" > /dev/null 2>&1; then
    print_status "Service health check passed"
else
    print_warning "Service health check failed, but service might still be starting"
fi

echo ""
print_status "Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Access your application at: $SERVICE_URL"
echo "2. Monitor logs: gcloud logs tail --service=$SERVICE_NAME --region=$REGION"
echo "3. Update service: gcloud run deploy $SERVICE_NAME --image=$GCR_IMAGE_NAME --region=$REGION"
echo "4. Delete service: gcloud run services delete $SERVICE_NAME --region=$REGION" 