#!/bin/bash

# Pre-deployment verification script for MyFolio FastAPI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 MyFolio FastAPI - Pre-deployment Verification${NC}"
echo "================================================="

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found. Please run this script from the api directory."
    exit 1
fi

print_info "Checking project structure..."

# Check required files
required_files=(
    "requirements.txt"
    "Dockerfile"
    "cloudbuild.yaml"
    "app.yaml"
    "deploy.sh"
    "app/main.py"
    "app/config.py"
    "app/cloud_config.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "Found $file"
    else
        print_error "Missing $file"
    fi
done

# Check environment files
if [ -f ".env" ]; then
    print_success "Found .env file"
else
    print_warning "No .env file found (optional for production)"
fi

if [ -f ".env.template" ]; then
    print_success "Found .env.template file"
else
    print_warning "No .env.template file found"
fi

if [ -f "service-account.json" ]; then
    print_success "Found Firebase service account file"
else
    print_warning "No service-account.json found (will need to be created for Firebase)"
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    print_success "Docker is installed"
    
    # Test Docker build
    print_info "Testing Docker build..."
    if docker build -t myfolio-api-test . > /dev/null 2>&1; then
        print_success "Docker build successful"
        docker rmi myfolio-api-test > /dev/null 2>&1 || true
    else
        print_error "Docker build failed"
    fi
else
    print_error "Docker is not installed"
fi

# Check if gcloud is available
if command -v gcloud &> /dev/null; then
    print_success "Google Cloud SDK is installed"
    
    # Check authentication
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        print_success "Authenticated as: $ACTIVE_ACCOUNT"
        
        # Check current project
        CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -n "$CURRENT_PROJECT" ]; then
            print_success "Current project: $CURRENT_PROJECT"
        else
            print_warning "No project set. Run: gcloud config set project YOUR_PROJECT_ID"
        fi
    else
        print_warning "Not authenticated with gcloud. Run: gcloud auth login"
    fi
else
    print_error "Google Cloud SDK is not installed"
fi

# Check Python dependencies
if command -v python3 &> /dev/null; then
    print_success "Python 3 is installed"
    
    print_info "Checking Python dependencies..."
    if pip3 show fastapi > /dev/null 2>&1; then
        print_success "FastAPI is installed"
    else
        print_warning "FastAPI not installed. Run: pip install -r requirements.txt"
    fi
else
    print_error "Python 3 is not installed"
fi

# Check deploy script permissions
if [ -x "deploy.sh" ]; then
    print_success "deploy.sh is executable"
else
    print_warning "deploy.sh is not executable. Run: chmod +x deploy.sh"
fi

echo ""
print_info "Verification complete!"
echo ""
echo "Next steps:"
echo "1. Make sure you have a GCP project created"
echo "2. Update PROJECT_ID in deploy.sh"
echo "3. Create Firebase service account and save as service-account.json"
echo "4. Set up your environment variables (see .env.template)"
echo "5. Run ./deploy.sh to deploy to GCP"
echo ""
echo "For detailed instructions, see: GCP_DEPLOYMENT.md"
