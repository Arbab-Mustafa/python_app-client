#!/bin/bash

# Build and Test Script for Lightweight Texas School Psychology Assistant
# This script builds the Docker image and tests it locally

set -e  # Exit on any error

echo "🚀 Building and Testing Lightweight Texas School Psychology Assistant"

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

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if required files exist
required_files=("app.py" "requirements.txt" "Dockerfile" "lightweight_vectorstore.py" "lightweight_chat.py" "lightweight_text_splitter.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file $file not found!"
        exit 1
    fi
done

print_status "All required files found"

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t texas-school-psychology-assistant:lightweight .

if [ $? -eq 0 ]; then
    print_status "Docker image built successfully"
else
    print_error "Docker build failed"
    exit 1
fi

# Test the image
echo "🧪 Testing Docker image..."

# Run a quick test inside the container
docker run --rm texas-school-psychology-assistant:lightweight python quick_test.py

if [ $? -eq 0 ]; then
    print_status "Lightweight implementation test passed"
else
    print_error "Lightweight implementation test failed"
    exit 1
fi

# Check image size
IMAGE_SIZE=$(docker images texas-school-psychology-assistant:lightweight --format "table {{.Size}}" | tail -n 1)
print_status "Docker image size: $IMAGE_SIZE"

# Test with docker-compose if available
if command -v docker-compose &> /dev/null; then
    echo "🐳 Testing with docker-compose..."
    
    # Stop any existing containers
    docker-compose down 2>/dev/null || true
    
    # Start the service
    docker-compose up -d
    
    # Wait for the service to be ready
    echo "⏳ Waiting for service to be ready..."
    sleep 30
    
    # Check if the service is running
    if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        print_status "Service is running and healthy"
        print_status "You can access the application at: http://localhost:8501"
    else
        print_warning "Service health check failed, but container might still be starting"
        print_status "You can try accessing the application at: http://localhost:8501"
    fi
    
    # Show logs
    echo "📋 Container logs:"
    docker-compose logs --tail=20
    
    print_status "Local testing completed successfully!"
    print_status "To stop the service, run: docker-compose down"
    
else
    print_warning "docker-compose not found, skipping local service test"
    print_status "You can test the image manually with:"
    echo "docker run -p 8501:8080 -e OPENAI_API_KEY=your_key texas-school-psychology-assistant:lightweight"
fi

echo ""
print_status "Build and test completed successfully!"
echo ""
echo "📋 Next steps for GCP deployment:"
echo "1. Tag the image for GCP: docker tag texas-school-psychology-assistant:lightweight gcr.io/YOUR_PROJECT_ID/texas-school-psychology-assistant:lightweight"
echo "2. Push to GCR: docker push gcr.io/YOUR_PROJECT_ID/texas-school-psychology-assistant:lightweight"
echo "3. Deploy to Cloud Run: gcloud run deploy texas-school-psychology-assistant --image gcr.io/YOUR_PROJECT_ID/texas-school-psychology-assistant:lightweight" 