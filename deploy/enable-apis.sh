#!/bin/bash

# Enable required Google Cloud APIs for Sage Financial Management App
# Robust version with retry logic and better error handling

# Don't exit on error immediately - we want to handle them gracefully
set +e

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

# List of required APIs (streamlined to essential ones)
APIS=(
    "cloudbuild.googleapis.com"          # Cloud Build for container building
    "run.googleapis.com"                 # Cloud Run for hosting applications
    "firestore.googleapis.com"           # Firestore for database
    "iam.googleapis.com"                 # Identity and Access Management
    "secretmanager.googleapis.com"       # Secret Manager for sensitive data
    "logging.googleapis.com"             # Cloud Logging
    "monitoring.googleapis.com"          # Cloud Monitoring
)

# Function to enable a single API with retry logic
enable_api() {
    local api=$1
    local max_retries=3
    local retry_count=0
    
    log_info "Enabling $api..."
    
    while [ $retry_count -lt $max_retries ]; do
        if gcloud services enable "$api" --project="$PROJECT_ID" --quiet 2>/dev/null; then
            log_success "✅ $api enabled"
            return 0
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                log_info "   Retry $retry_count/$max_retries for $api..."
                sleep 2
            fi
        fi
    done
    
    log_error "❌ Failed to enable $api after $max_retries attempts"
    return 1
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

# Check if critical APIs failed
critical_apis=("cloudbuild.googleapis.com" "run.googleapis.com" "firestore.googleapis.com")
critical_failed=()

for api in "${failed_apis[@]}"; do
    for critical in "${critical_apis[@]}"; do
        if [[ "$api" == "$critical" ]]; then
            critical_failed+=("$api")
        fi
    done
done

if [[ ${#failed_apis[@]} -gt 0 ]]; then
    echo ""
    log_error "Failed to enable the following APIs:"
    for api in "${failed_apis[@]}"; do
        echo "  - $api"
    done
    echo ""
    
    if [[ ${#critical_failed[@]} -gt 0 ]]; then
        log_error "Critical APIs failed. Cannot continue deployment."
        log_error "Please check your permissions and billing status."
        exit 1
    else
        log_info "Non-critical APIs failed, but continuing with deployment..."
    fi
fi

echo ""
log_success "All required APIs are now enabled!"

# Wait for APIs to be fully activated
log_info "Waiting for APIs to be fully activated..."
sleep 10

# Verify critical APIs are working (with retries)
log_info "Verifying API activation..."

# Test Cloud Run API with retry
verify_api() {
    local api_name=$1
    local test_command=$2
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if eval "$test_command" >/dev/null 2>&1; then
            log_success "✅ $api_name is active"
            return 0
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                log_info "   Waiting for $api_name to activate... ($retry_count/$max_retries)"
                sleep 5
            fi
        fi
    done
    
    log_error "❌ $api_name verification failed after $max_retries attempts"
    return 1
}

# Verify APIs
verify_api "Cloud Run API" "gcloud run regions list --project=\"$PROJECT_ID\""
verify_api "Firestore API" "gcloud firestore databases list --project=\"$PROJECT_ID\""

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