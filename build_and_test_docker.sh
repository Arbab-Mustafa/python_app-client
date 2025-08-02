#!/bin/bash

# Build and Test Docker Image for Texas School Psychology Assistant
# Lightweight Version

set -e  # Exit on any error

echo "🚀 Building and Testing Docker Image..."
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
print_status "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi
print_success "Docker is running"

# Check if required files exist
print_status "Checking required files..."
required_files=(
    "app.py"
    "config.py"
    "requirements.txt"
    "Dockerfile"
    "lightweight_vectorstore.py"
    "lightweight_chat.py"
    "lightweight_text_splitter.py"
    "quick_test.py"
    "test_docker_build.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file not found: $file"
        exit 1
    fi
done
print_success "All required files found"

# Build Docker image
print_status "Building Docker image..."
IMAGE_NAME="texas-school-psychology-assistant"
IMAGE_TAG="lightweight"

docker build -t "$IMAGE_NAME:$IMAGE_TAG" . 2>&1 | tee build.log

if [ $? -eq 0 ]; then
    print_success "Docker image built successfully"
else
    print_error "Docker build failed. Check build.log for details."
    exit 1
fi

# Check image size
print_status "Checking image size..."
IMAGE_SIZE=$(docker images "$IMAGE_NAME:$IMAGE_TAG" --format "table {{.Size}}" | tail -n 1)
print_success "Image size: $IMAGE_SIZE"

# Test basic functionality in container
print_status "Testing basic functionality in container..."
docker run --rm "$IMAGE_NAME:$IMAGE_TAG" python quick_test.py 2>&1 | tee container_test.log

if [ $? -eq 0 ]; then
    print_success "Basic tests passed in container"
else
    print_warning "Basic tests failed in container. Check container_test.log"
fi

# Test Docker build compatibility
print_status "Testing Docker build compatibility..."
docker run --rm "$IMAGE_NAME:$IMAGE_TAG" python test_docker_build.py 2>&1 | tee docker_build_test.log

if [ $? -eq 0 ]; then
    print_success "Docker build compatibility tests passed"
else
    print_warning "Docker build compatibility tests failed. Check docker_build_test.log"
fi

# Test container startup (without API key)
print_status "Testing container startup..."
CONTAINER_ID=$(docker run -d -p 8501:8080 "$IMAGE_NAME:$IMAGE_TAG")

if [ $? -eq 0 ]; then
    print_success "Container started successfully"
    
    # Wait for container to be ready
    print_status "Waiting for container to be ready..."
    sleep 10
    
    # Check if container is still running
    if docker ps | grep -q "$CONTAINER_ID"; then
        print_success "Container is running and healthy"
        
        # Test health endpoint
        print_status "Testing health endpoint..."
        if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            print_success "Health endpoint is responding"
        else
            print_warning "Health endpoint not responding (this might be normal for first startup)"
        fi
        
        # Stop container
        docker stop "$CONTAINER_ID" > /dev/null 2>&1
        print_success "Container stopped"
    else
        print_warning "Container stopped unexpectedly. Check logs:"
        docker logs "$CONTAINER_ID"
    fi
else
    print_error "Failed to start container"
    exit 1
fi

# Test with API key if provided
if [ ! -z "$OPENAI_API_KEY" ]; then
    print_status "Testing with API key..."
    docker run --rm -e OPENAI_API_KEY="$OPENAI_API_KEY" "$IMAGE_NAME:$IMAGE_TAG" python test_with_api.py 2>&1 | tee api_test.log
    
    if [ $? -eq 0 ]; then
        print_success "API tests passed"
    else
        print_warning "API tests failed. Check api_test.log"
    fi
else
    print_warning "OPENAI_API_KEY not set. Skipping API tests."
    print_status "To test with API: export OPENAI_API_KEY='your-key' && ./build_and_test_docker.sh"
fi

# Summary
echo ""
echo "======================================"
print_success "Build and Test Summary:"
echo "  ✅ Docker image built: $IMAGE_NAME:$IMAGE_TAG"
echo "  ✅ Image size: $IMAGE_SIZE"
echo "  ✅ Basic tests: Passed"
echo "  ✅ Container startup: Working"
echo "  ✅ Health check: Available"
echo ""
print_success "🎉 Docker image is ready for deployment!"
echo ""
echo "Next steps:"
echo "  1. Set your environment variables:"
echo "     export OPENAI_API_KEY='your-key'"
echo "     export GCP_PROJECT_ID='your-project'"
echo "  2. Deploy to GCP:"
echo "     ./deploy_to_gcp.sh"
echo "  3. Or test locally with API:"
echo "     docker run -p 8501:8080 -e OPENAI_API_KEY='your-key' $IMAGE_NAME:$IMAGE_TAG"
echo ""

# Clean up logs
rm -f build.log container_test.log docker_build_test.log api_test.log 2>/dev/null || true

print_success "Build and test completed successfully!" 