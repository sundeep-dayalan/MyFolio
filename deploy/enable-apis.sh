#!/bin/bash

# Enable required Google Cloud APIs for Sage Financial Management App

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[API-ENABLE]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[API-ENABLE]${NC} $1"
}

log_error() {
    echo -e "${RED}[API-ENABLE]${NC} $1"
}

# Check if PROJECT_ID is set
if [[ -z "$PROJECT_ID" ]]; then
    log_error "PROJECT_ID environment variable not set"
    exit 1
fi

log_info "Enabling Google Cloud APIs for project: $PROJECT_ID"

# List of required APIs
APIS=(
    "cloudbuild.googleapis.com"          # Cloud Build for container building
    "run.googleapis.com"                 # Cloud Run for hosting applications
    "firestore.googleapis.com"           # Firestore for database
    "firebase.googleapis.com"            # Firebase services
    "identitytoolkit.googleapis.com"     # Identity Toolkit for authentication
    "oauth2.googleapis.com"              # OAuth 2.0 for Google sign-in
    "iam.googleapis.com"                 # Identity and Access Management
    "cloudresourcemanager.googleapis.com" # Resource Manager
    "logging.googleapis.com"             # Cloud Logging
    "monitoring.googleapis.com"          # Cloud Monitoring
    "secretmanager.googleapis.com"       # Secret Manager for sensitive data
    "artifactregistry.googleapis.com"    # Artifact Registry for container images
)

# Function to enable a single API
enable_api() {
    local api=$1
    log_info "Enabling $api..."
    
    if gcloud services enable "$api" --project="$PROJECT_ID" 2>/dev/null; then
        log_success "✅ $api enabled"
        return 0
    else
        log_error "❌ Failed to enable $api"
        return 1
    fi
}

# Function to check if API is already enabled
is_api_enabled() {
    local api=$1
    gcloud services list --enabled --filter="name:$api" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | grep -q "$api"
}

log_info "Checking and enabling required APIs..."
echo ""

failed_apis=()
enabled_count=0
skipped_count=0

for api in "${APIS[@]}"; do
    if is_api_enabled "$api"; then
        log_info "⏭️  $api (already enabled)"
        ((skipped_count++))
    else
        if enable_api "$api"; then
            ((enabled_count++))
        else
            failed_apis+=("$api")
        fi
    fi
    
    # Small delay to avoid rate limiting
    sleep 1
done

echo ""
log_info "API enablement summary:"
echo "  ✅ Newly enabled: $enabled_count"
echo "  ⏭️  Already enabled: $skipped_count"
echo "  ❌ Failed: ${#failed_apis[@]}"

if [[ ${#failed_apis[@]} -gt 0 ]]; then
    echo ""
    log_error "Failed to enable the following APIs:"
    for api in "${failed_apis[@]}"; do
        echo "  - $api"
    done
    echo ""
    log_error "Please check your permissions and try again."
    log_error "You may need to enable billing on your project."
    exit 1
fi

echo ""
log_success "All required APIs are now enabled!"

# Wait for APIs to be fully activated
log_info "Waiting for APIs to be fully activated..."
sleep 10

# Verify critical APIs are working
log_info "Verifying API activation..."

# Test Cloud Run API
if gcloud run regions list --project="$PROJECT_ID" >/dev/null 2>&1; then
    log_success "✅ Cloud Run API is active"
else
    log_error "❌ Cloud Run API verification failed"
    exit 1
fi

# Test Firestore API
if gcloud firestore databases list --project="$PROJECT_ID" >/dev/null 2>&1; then
    log_success "✅ Firestore API is active"
else
    log_error "❌ Firestore API verification failed"
    exit 1
fi

echo ""
log_success "🎉 All APIs successfully enabled and verified!"

# Create default Firestore database if it doesn't exist
log_info "Checking Firestore database..."

# Check if default database exists
if ! gcloud firestore databases describe --database="(default)" --project="$PROJECT_ID" >/dev/null 2>&1; then
    log_info "Creating default Firestore database..."
    
    # Create Firestore database in Native mode
    if gcloud firestore databases create --database="(default)" --location="us-central" --type=firestore-native --project="$PROJECT_ID"; then
        log_success "✅ Firestore database created"
    else
        log_error "❌ Failed to create Firestore database"
        log_error "Please create it manually in the Google Cloud Console"
        exit 1
    fi
else
    log_success "✅ Firestore database already exists"
fi

echo ""
log_success "🚀 Infrastructure setup complete! Ready for deployment."