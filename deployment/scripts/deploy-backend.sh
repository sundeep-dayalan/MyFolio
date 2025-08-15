#!/bin/bash

# Backend deployment script for Sage Financial Management App
# This script builds and deploys the FastAPI backend to Google Cloud Run

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVER_DIR="$PROJECT_ROOT/server"

# Default values
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="sage-backend"
REPOSITORY="sage-repo"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --service-name)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --repository)
            REPOSITORY="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --project-id PROJECT_ID [OPTIONS]"
            echo "Options:"
            echo "  --project-id       GCP Project ID (required)"
            echo "  --region           GCP Region (default: us-central1)"
            echo "  --service-name     Cloud Run service name (default: sage-backend)"
            echo "  --repository       Artifact Registry repository (default: sage-repo)"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$PROJECT_ID" ]]; then
    log_error "Project ID is required. Use --project-id flag."
    exit 1
fi

# Check if required tools are installed
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v gcloud &> /dev/null; then
        missing_deps+=("gcloud")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install them and try again."
        exit 1
    fi
    
    log_success "All dependencies are installed"
}

# Authenticate with Google Cloud
authenticate_gcp() {
    log_info "Configuring Google Cloud..."
    
    gcloud config set project "$PROJECT_ID"
    gcloud config set run/region "$REGION"
    
    # Configure Docker to use gcloud as a credential helper
    gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
    
    log_success "Google Cloud configured"
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building Docker image..."
    
    cd "$SERVER_DIR"
    
    # Image names
    local image_name="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$SERVICE_NAME"
    local commit_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    local image_tag="$image_name:$commit_sha"
    local latest_tag="$image_name:latest"
    
    # Build the Docker image
    docker build -t "$image_tag" -t "$latest_tag" .
    
    log_info "Pushing Docker image to Artifact Registry..."
    
    # Push both tags
    docker push "$image_tag"
    docker push "$latest_tag"
    
    log_success "Docker image pushed successfully"
    echo "$image_tag"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    local image_tag="$1"
    
    log_info "Deploying to Cloud Run..."
    
    gcloud run deploy "$SERVICE_NAME" \
        --image="$image_tag" \
        --region="$REGION" \
        --platform=managed \
        --allow-unauthenticated \
        --port=8000 \
        --memory=1Gi \
        --cpu=1 \
        --max-instances=10 \
        --set-env-vars="ENVIRONMENT=production,DEBUG=false" \
        --set-secrets="SECRET_KEY=SECRET_KEY:latest" \
        --set-secrets="FIREBASE_PROJECT_ID=FIREBASE_PROJECT_ID:latest" \
        --set-secrets="GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest" \
        --set-secrets="GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest" \
        --set-secrets="PLAID_CLIENT_ID=PLAID_CLIENT_ID:latest" \
        --set-secrets="PLAID_SECRET=PLAID_SECRET:latest" \
        --set-secrets="PLAID_ENV=PLAID_ENV:latest" \
        --set-secrets="FIREBASE_CREDENTIALS=FIREBASE_CREDENTIALS:latest" \
        --quiet
    
    log_success "Backend deployed to Cloud Run"
}

# Get service URL
get_service_url() {
    local service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")
    
    log_success "Backend service URL: $service_url"
    echo "$service_url"
}

# Health check
health_check() {
    local service_url="$1"
    
    log_info "Performing health check..."
    
    # Wait a bit for the service to be ready
    sleep 10
    
    if curl -f -s "$service_url/health" > /dev/null; then
        log_success "Health check passed"
    else
        log_warning "Health check failed. Service might still be starting up."
    fi
}

# Main deployment function
main() {
    log_info "Starting backend deployment for project: $PROJECT_ID"
    
    check_dependencies
    authenticate_gcp
    
    local image_tag
    image_tag=$(build_and_push_image)
    
    deploy_to_cloud_run "$image_tag"
    
    local service_url
    service_url=$(get_service_url)
    
    health_check "$service_url"
    
    log_success "Backend deployment completed successfully!"
    log_info "Service URL: $service_url"
    log_info "You can view logs with: gcloud run services logs tail $SERVICE_NAME --region=$REGION"
}

# Run main function
main "$@"