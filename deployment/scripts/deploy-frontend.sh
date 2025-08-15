#!/bin/bash

# Frontend deployment script for Sage Financial Management App
# This script builds and deploys the React frontend to Firebase Hosting

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
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Default values
PROJECT_ID=""
BACKEND_URL=""
ENVIRONMENT="production"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --backend-url)
            BACKEND_URL="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --project-id PROJECT_ID --backend-url BACKEND_URL [OPTIONS]"
            echo "Options:"
            echo "  --project-id       GCP Project ID (required)"
            echo "  --backend-url      Backend service URL (required)"
            echo "  --environment      Environment (default: production)"
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

if [[ -z "$BACKEND_URL" ]]; then
    log_error "Backend URL is required. Use --backend-url flag."
    exit 1
fi

# Check if required tools are installed
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v npm &> /dev/null; then
        missing_deps+=("npm")
    fi
    
    if ! command -v firebase &> /dev/null; then
        missing_deps+=("firebase-tools")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        if [[ " ${missing_deps[*]} " =~ " firebase-tools " ]]; then
            log_error "Install Firebase CLI with: npm install -g firebase-tools"
        fi
        exit 1
    fi
    
    log_success "All dependencies are installed"
}

# Configure Firebase project
configure_firebase() {
    log_info "Configuring Firebase project..."
    
    cd "$FRONTEND_DIR"
    
    # Set Firebase project
    firebase use "$PROJECT_ID" --add
    
    log_success "Firebase project configured"
}

# Create production environment file
create_env_file() {
    log_info "Creating production environment configuration..."
    
    cd "$FRONTEND_DIR"
    
    # Create .env.production file
    cat > .env.production << EOF
# Production environment configuration
VITE_API_BASE_URL=$BACKEND_URL/api/v1
VITE_APP_ENV=$ENVIRONMENT
VITE_FIREBASE_PROJECT_ID=$PROJECT_ID
EOF
    
    log_success "Environment configuration created"
}

# Install dependencies
install_dependencies() {
    log_info "Installing frontend dependencies..."
    
    cd "$FRONTEND_DIR"
    
    npm ci --prefer-offline --no-audit
    
    log_success "Dependencies installed"
}

# Build the application
build_application() {
    log_info "Building React application..."
    
    cd "$FRONTEND_DIR"
    
    # Run the build
    npm run build
    
    # Check if build was successful
    if [[ ! -d "dist" ]]; then
        log_error "Build failed: dist directory not found"
        exit 1
    fi
    
    log_success "Application built successfully"
}

# Run tests (if available)
run_tests() {
    log_info "Running tests..."
    
    cd "$FRONTEND_DIR"
    
    # Check if test script exists
    if npm run test --dry-run &> /dev/null; then
        npm run test -- --run --reporter=verbose
        log_success "Tests passed"
    else
        log_warning "No test script found, skipping tests"
    fi
}

# Deploy to Firebase Hosting
deploy_to_firebase() {
    log_info "Deploying to Firebase Hosting..."
    
    cd "$FRONTEND_DIR"
    
    # Deploy to Firebase Hosting
    firebase deploy --only hosting --project "$PROJECT_ID"
    
    log_success "Frontend deployed to Firebase Hosting"
}

# Get hosting URL
get_hosting_url() {
    local hosting_url="https://$PROJECT_ID.web.app"
    
    log_success "Frontend URL: $hosting_url"
    echo "$hosting_url"
}

# Health check
health_check() {
    local hosting_url="$1"
    
    log_info "Performing health check..."
    
    # Wait a bit for the deployment to propagate
    sleep 10
    
    if curl -f -s "$hosting_url" > /dev/null; then
        log_success "Health check passed"
    else
        log_warning "Health check failed. Site might still be propagating."
    fi
}

# Update Firebase configuration
update_firebase_config() {
    log_info "Updating Firebase Hosting configuration..."
    
    cd "$FRONTEND_DIR"
    
    # Create or update firebase.json with enhanced configuration
    cat > firebase.json << EOF
{
  "hosting": {
    "public": "dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      },
      {
        "source": "**/index.html",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "no-cache, no-store, must-revalidate"
          }
        ]
      }
    ]
  }
}
EOF
    
    log_success "Firebase configuration updated"
}

# Main deployment function
main() {
    log_info "Starting frontend deployment for project: $PROJECT_ID"
    log_info "Backend URL: $BACKEND_URL"
    
    check_dependencies
    configure_firebase
    update_firebase_config
    create_env_file
    install_dependencies
    run_tests
    build_application
    deploy_to_firebase
    
    local hosting_url
    hosting_url=$(get_hosting_url)
    
    health_check "$hosting_url"
    
    log_success "Frontend deployment completed successfully!"
    log_info "Frontend URL: $hosting_url"
    log_info "You can view hosting logs with: firebase functions:log --project $PROJECT_ID"
}

# Run main function
main "$@"