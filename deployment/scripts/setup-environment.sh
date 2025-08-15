#!/bin/bash

# Environment setup script for Sage Financial Management App
# This script helps configure required environment variables and secrets

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

# Default values
PROJECT_ID=""
INTERACTIVE=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --non-interactive)
            INTERACTIVE=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 --project-id PROJECT_ID [OPTIONS]"
            echo "Options:"
            echo "  --project-id       GCP Project ID (required)"
            echo "  --non-interactive  Run in non-interactive mode"
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
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    log_success "All dependencies are installed"
}

# Prompt for input with validation
prompt_for_input() {
    local prompt="$1"
    local var_name="$2"
    local is_secret="${3:-false}"
    local default_value="${4:-}"
    
    if [[ "$INTERACTIVE" == "false" ]]; then
        if [[ -n "$default_value" ]]; then
            echo "$default_value"
        else
            log_error "Non-interactive mode requires all values to be provided"
            exit 1
        fi
        return
    fi
    
    while true; do
        if [[ "$is_secret" == "true" ]]; then
            read -s -p "$prompt: " input
            echo
        else
            if [[ -n "$default_value" ]]; then
                read -p "$prompt [$default_value]: " input
                input="${input:-$default_value}"
            else
                read -p "$prompt: " input
            fi
        fi
        
        if [[ -n "$input" ]]; then
            echo "$input"
            break
        else
            log_error "This field is required. Please provide a value."
        fi
    done
}

# Configure Google Cloud
configure_gcloud() {
    log_info "Configuring Google Cloud..."
    
    gcloud config set project "$PROJECT_ID"
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
        log_info "Please authenticate with Google Cloud..."
        gcloud auth login
    fi
    
    log_success "Google Cloud configured"
}

# Gather environment variables
gather_environment_variables() {
    log_info "Gathering environment variables..."
    echo
    log_info "Please provide the following configuration values:"
    echo
    
    # Plaid configuration
    log_info "=== Plaid Configuration ==="
    PLAID_CLIENT_ID=$(prompt_for_input "Plaid Client ID" "PLAID_CLIENT_ID" "false")
    PLAID_SECRET=$(prompt_for_input "Plaid Secret" "PLAID_SECRET" "true")
    PLAID_ENV=$(prompt_for_input "Plaid Environment (sandbox/production)" "PLAID_ENV" "false" "sandbox")
    
    echo
    
    # Google OAuth configuration
    log_info "=== Google OAuth Configuration ==="
    GOOGLE_CLIENT_ID=$(prompt_for_input "Google OAuth Client ID" "GOOGLE_CLIENT_ID" "false")
    GOOGLE_CLIENT_SECRET=$(prompt_for_input "Google OAuth Client Secret" "GOOGLE_CLIENT_SECRET" "true")
    
    echo
    
    log_success "Environment variables gathered"
}

# Create secrets in Google Secret Manager
create_secrets() {
    log_info "Creating secrets in Google Secret Manager..."
    
    local secrets=(
        "SECRET_KEY"
        "FIREBASE_PROJECT_ID"
        "GOOGLE_CLIENT_ID"
        "GOOGLE_CLIENT_SECRET"
        "PLAID_CLIENT_ID"
        "PLAID_SECRET"
        "PLAID_ENV"
        "FIREBASE_CREDENTIALS"
    )
    
    # Create secrets if they don't exist
    for secret in "${secrets[@]}"; do
        if ! gcloud secrets describe "$secret" --project="$PROJECT_ID" &> /dev/null; then
            log_info "Creating secret: $secret"
            gcloud secrets create "$secret" --project="$PROJECT_ID" --replication-policy="automatic"
        else
            log_info "Secret $secret already exists"
        fi
    done
    
    log_success "Secrets created in Secret Manager"
}

# Store secret values
store_secret_values() {
    log_info "Storing secret values..."
    
    # Generate JWT secret if not provided
    JWT_SECRET=$(openssl rand -base64 32)
    
    # Store secret values
    echo -n "$JWT_SECRET" | gcloud secrets versions add SECRET_KEY --data-file=- --project="$PROJECT_ID"
    echo -n "$PROJECT_ID" | gcloud secrets versions add FIREBASE_PROJECT_ID --data-file=- --project="$PROJECT_ID"
    echo -n "$GOOGLE_CLIENT_ID" | gcloud secrets versions add GOOGLE_CLIENT_ID --data-file=- --project="$PROJECT_ID"
    echo -n "$GOOGLE_CLIENT_SECRET" | gcloud secrets versions add GOOGLE_CLIENT_SECRET --data-file=- --project="$PROJECT_ID"
    echo -n "$PLAID_CLIENT_ID" | gcloud secrets versions add PLAID_CLIENT_ID --data-file=- --project="$PROJECT_ID"
    echo -n "$PLAID_SECRET" | gcloud secrets versions add PLAID_SECRET --data-file=- --project="$PROJECT_ID"
    echo -n "$PLAID_ENV" | gcloud secrets versions add PLAID_ENV --data-file=- --project="$PROJECT_ID"
    
    log_success "Secret values stored"
}

# Create local environment files
create_local_env_files() {
    log_info "Creating local environment files..."
    
    # Backend .env file
    cat > "$PROJECT_ROOT/server/.env" << EOF
# Backend Environment Configuration
SECRET_KEY=$JWT_SECRET
FIREBASE_PROJECT_ID=$PROJECT_ID
GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET
PLAID_CLIENT_ID=$PLAID_CLIENT_ID
PLAID_SECRET=$PLAID_SECRET
PLAID_ENV=$PLAID_ENV
ENVIRONMENT=development
DEBUG=true
EOF
    
    # Frontend .env.development file
    cat > "$PROJECT_ROOT/frontend/.env.development" << EOF
# Frontend Development Environment Configuration
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_ENV=development
VITE_FIREBASE_PROJECT_ID=$PROJECT_ID
EOF
    
    # Frontend .env.production file (template)
    cat > "$PROJECT_ROOT/frontend/.env.production" << EOF
# Frontend Production Environment Configuration
# This will be updated during deployment
VITE_API_BASE_URL=https://your-backend-url/api/v1
VITE_APP_ENV=production
VITE_FIREBASE_PROJECT_ID=$PROJECT_ID
EOF
    
    log_success "Local environment files created"
}

# Setup OAuth consent screen
setup_oauth_consent() {
    log_info "Setting up OAuth consent screen..."
    
    cat << EOF

=== OAuth Setup Instructions ===

1. Go to the Google Cloud Console: https://console.cloud.google.com/
2. Navigate to APIs & Services > Credentials
3. Create OAuth 2.0 Client ID (if not already created)
4. Configure the OAuth consent screen:
   - Application name: Sage Financial Management
   - Authorized domains: Add your domain
   - Scopes: email, profile, openid

5. Add authorized redirect URIs:
   - For development: http://localhost:5173/auth/callback
   - For production: https://$PROJECT_ID.web.app/auth/callback

EOF
    
    if [[ "$INTERACTIVE" == "true" ]]; then
        read -p "Press Enter after completing OAuth setup..."
    fi
}

# Display summary
display_summary() {
    log_success "Environment setup completed!"
    
    cat << EOF

=== Summary ===

✅ Google Cloud project configured: $PROJECT_ID
✅ Secrets created in Secret Manager
✅ Environment variables stored
✅ Local development files created

Next steps:
1. Complete OAuth consent screen setup (see instructions above)
2. Run infrastructure deployment: cd deployment/terraform && terraform apply
3. Deploy backend: ./deployment/scripts/deploy-backend.sh --project-id $PROJECT_ID
4. Deploy frontend: ./deployment/scripts/deploy-frontend.sh --project-id $PROJECT_ID --backend-url [BACKEND_URL]

Local development:
- Backend: cd server && python3 run.py
- Frontend: cd frontend && npm run dev

EOF
}

# Main function
main() {
    log_info "Starting environment setup for project: $PROJECT_ID"
    
    check_dependencies
    configure_gcloud
    gather_environment_variables
    create_secrets
    store_secret_values
    create_local_env_files
    setup_oauth_consent
    display_summary
}

# Run main function
main "$@"