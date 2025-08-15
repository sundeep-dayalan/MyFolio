#!/bin/bash

# Main deployment orchestration script for Sage Financial Management App
# This script automates the complete deployment process

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
PROJECT_ID=""
REGION="us-central1"
SKIP_TERRAFORM=false
SKIP_BACKEND=false
SKIP_FRONTEND=false
TERRAFORM_VARS_FILE=""
SERVICE_ACCOUNT_KEY=""

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
        --terraform-vars)
            TERRAFORM_VARS_FILE="$2"
            shift 2
            ;;
        --service-account-key)
            SERVICE_ACCOUNT_KEY="$2"
            shift 2
            ;;
        --skip-terraform)
            SKIP_TERRAFORM=true
            shift
            ;;
        --skip-backend)
            SKIP_BACKEND=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        -h|--help)
            cat << EOF
Usage: $0 --project-id PROJECT_ID [OPTIONS]

This script automates the complete deployment of the Sage Financial Management App
to Google Cloud Platform using Terraform for infrastructure and custom scripts
for application deployment.

Required:
  --project-id              GCP Project ID

Optional:
  --region                  GCP Region (default: us-central1)
  --terraform-vars          Path to terraform.tfvars file
  --service-account-key     Path to service account key file (for CI/CD)
  --skip-terraform          Skip Terraform infrastructure deployment
  --skip-backend            Skip backend deployment
  --skip-frontend           Skip frontend deployment
  -h, --help                Show this help message

Examples:
  # Full deployment
  $0 --project-id my-project

  # Deploy with custom terraform vars
  $0 --project-id my-project --terraform-vars ./terraform.tfvars

  # Deploy only application (skip infrastructure)
  $0 --project-id my-project --skip-terraform

  # CI/CD deployment with service account
  $0 --project-id my-project --service-account-key ./sa-key.json

EOF
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
    log_step "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v gcloud &> /dev/null; then
        missing_deps+=("gcloud")
    fi
    
    if ! command -v terraform &> /dev/null && [[ "$SKIP_TERRAFORM" == "false" ]]; then
        missing_deps+=("terraform")
    fi
    
    if ! command -v docker &> /dev/null && [[ "$SKIP_BACKEND" == "false" ]]; then
        missing_deps+=("docker")
    fi
    
    if ! command -v npm &> /dev/null && [[ "$SKIP_FRONTEND" == "false" ]]; then
        missing_deps+=("npm")
    fi
    
    if ! command -v firebase &> /dev/null && [[ "$SKIP_FRONTEND" == "false" ]]; then
        missing_deps+=("firebase-tools")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install them and try again."
        exit 1
    fi
    
    log_success "All dependencies are available"
}

# Authenticate with Google Cloud
authenticate_gcp() {
    log_step "Authenticating with Google Cloud..."
    
    if [[ -n "$SERVICE_ACCOUNT_KEY" ]]; then
        log_info "Using service account authentication"
        gcloud auth activate-service-account --key-file="$SERVICE_ACCOUNT_KEY"
    else
        log_info "Using user authentication"
        if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
            gcloud auth login
        fi
    fi
    
    gcloud config set project "$PROJECT_ID"
    
    log_success "Google Cloud authentication configured"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    if [[ "$SKIP_TERRAFORM" == "true" ]]; then
        log_warning "Skipping Terraform infrastructure deployment"
        return
    fi
    
    log_step "Deploying infrastructure with Terraform..."
    
    cd "$SCRIPT_DIR/terraform"
    
    # Initialize Terraform
    terraform init
    
    # Validate configuration
    terraform validate
    
    # Plan deployment
    local tf_plan_args=()
    if [[ -n "$TERRAFORM_VARS_FILE" ]]; then
        tf_plan_args+=("-var-file=$TERRAFORM_VARS_FILE")
    fi
    
    terraform plan "${tf_plan_args[@]}" -out=tfplan
    
    # Apply infrastructure
    terraform apply tfplan
    
    # Get outputs
    BACKEND_URL=$(terraform output -raw backend_url)
    
    log_success "Infrastructure deployed successfully"
    log_info "Backend URL: $BACKEND_URL"
    
    cd "$PROJECT_ROOT"
}

# Deploy backend application
deploy_backend() {
    if [[ "$SKIP_BACKEND" == "true" ]]; then
        log_warning "Skipping backend deployment"
        return
    fi
    
    log_step "Deploying backend application..."
    
    "$SCRIPT_DIR/scripts/deploy-backend.sh" \
        --project-id "$PROJECT_ID" \
        --region "$REGION"
    
    # Get backend URL if not set from Terraform
    if [[ -z "${BACKEND_URL:-}" ]]; then
        BACKEND_URL=$(gcloud run services describe sage-backend \
            --region="$REGION" \
            --format="value(status.url)")
    fi
    
    log_success "Backend deployed successfully"
    log_info "Backend URL: $BACKEND_URL"
}

# Deploy frontend application
deploy_frontend() {
    if [[ "$SKIP_FRONTEND" == "true" ]]; then
        log_warning "Skipping frontend deployment"
        return
    fi
    
    if [[ -z "${BACKEND_URL:-}" ]]; then
        log_error "Backend URL is required for frontend deployment"
        exit 1
    fi
    
    log_step "Deploying frontend application..."
    
    "$SCRIPT_DIR/scripts/deploy-frontend.sh" \
        --project-id "$PROJECT_ID" \
        --backend-url "$BACKEND_URL"
    
    FRONTEND_URL="https://$PROJECT_ID.web.app"
    
    log_success "Frontend deployed successfully"
    log_info "Frontend URL: $FRONTEND_URL"
}

# Run post-deployment checks
post_deployment_checks() {
    log_step "Running post-deployment checks..."
    
    local checks_passed=0
    local total_checks=0
    
    # Check backend health
    if [[ -n "${BACKEND_URL:-}" ]]; then
        total_checks=$((total_checks + 1))
        log_info "Checking backend health..."
        if curl -f -s "$BACKEND_URL/health" > /dev/null; then
            log_success "✅ Backend health check passed"
            checks_passed=$((checks_passed + 1))
        else
            log_warning "❌ Backend health check failed"
        fi
    fi
    
    # Check frontend accessibility
    if [[ -n "${FRONTEND_URL:-}" ]]; then
        total_checks=$((total_checks + 1))
        log_info "Checking frontend accessibility..."
        if curl -f -s "$FRONTEND_URL" > /dev/null; then
            log_success "✅ Frontend accessibility check passed"
            checks_passed=$((checks_passed + 1))
        else
            log_warning "❌ Frontend accessibility check failed"
        fi
    fi
    
    log_info "Post-deployment checks: $checks_passed/$total_checks passed"
}

# Display deployment summary
display_summary() {
    log_success "🎉 Deployment completed!"
    
    cat << EOF

=====================================
   DEPLOYMENT SUMMARY
=====================================

Project ID: $PROJECT_ID
Region: $REGION

EOF
    
    if [[ -n "${BACKEND_URL:-}" ]]; then
        echo "Backend URL: $BACKEND_URL"
    fi
    
    if [[ -n "${FRONTEND_URL:-}" ]]; then
        echo "Frontend URL: $FRONTEND_URL"
    fi
    
    cat << EOF

=====================================
   NEXT STEPS
=====================================

1. 🔐 Configure OAuth redirect URIs:
   - Development: http://localhost:5173/auth/callback
   - Production: $FRONTEND_URL/auth/callback

2. 🧪 Test the application:
   - Open $FRONTEND_URL
   - Try logging in with Google
   - Connect a test account with Plaid

3. 📊 Monitor the deployment:
   - Backend logs: gcloud run services logs tail sage-backend --region=$REGION
   - Firebase hosting: firebase hosting:channel:list --project $PROJECT_ID

4. 🚀 Set up CI/CD (optional):
   - Configure GitHub Actions with service account
   - Set up automated deployments

For more information, see the documentation in docs/DEPLOYMENT.md

EOF
}

# Main deployment function
main() {
    cat << EOF
=====================================
   SAGE FINANCIAL MANAGEMENT
   AUTOMATED DEPLOYMENT
=====================================

Project: $PROJECT_ID
Region: $REGION

Starting deployment process...

EOF
    
    check_dependencies
    authenticate_gcp
    
    deploy_infrastructure
    deploy_backend
    deploy_frontend
    
    post_deployment_checks
    display_summary
}

# Handle script interruption
cleanup() {
    log_warning "Deployment interrupted"
    exit 1
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run main function
main "$@"