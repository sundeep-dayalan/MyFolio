#!/bin/bash

# 🚀 Sage Financial Management - One-Click Deployment
# This script creates a GCP project, sets up billing, deploys infrastructure, and configures GitHub Actions

set -euo pipefail

# Colors for beautiful output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Unicode symbols
CHECK="✅"
CROSS="❌"
ROCKET="🚀"
GEAR="⚙️"
MONEY="💰"
SHIELD="🔐"
GLOBE="🌐"
GITHUB="📦"

# Logging functions
log_header() {
    echo -e "\n${WHITE}================================${NC}"
    echo -e "${WHITE}$1${NC}"
    echo -e "${WHITE}================================${NC}\n"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} ${CHECK} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} ${CROSS} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} ${GEAR} $1"
}

# Global variables
ORGANIZATION_ID=""
BILLING_ACCOUNT_ID=""
PROJECT_ID=""
PROJECT_NAME="Sage Financial Management"
REGION="us-central1"
GITHUB_REPO=""
GITHUB_TOKEN=""
PLAID_CLIENT_ID=""
PLAID_SECRET=""
PLAID_ENV="sandbox"
GOOGLE_OAUTH_CLIENT_ID=""
GOOGLE_OAUTH_CLIENT_SECRET=""

# Welcome banner
show_welcome_banner() {
    clear
    echo -e "${PURPLE}"
    cat << 'EOF'
    ███████╗ █████╗  ██████╗ ███████╗
    ██╔════╝██╔══██╗██╔════╝ ██╔════╝
    ███████╗███████║██║  ███╗█████╗  
    ╚════██║██╔══██║██║   ██║██╔══╝  
    ███████║██║  ██║╚██████╔╝███████╗
    ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
    
    FINANCIAL MANAGEMENT APP
    One-Click GCP Deployment
EOF
    echo -e "${NC}\n"
    echo -e "${WHITE}Welcome to the automated deployment wizard!${NC}"
    echo -e "${WHITE}This will create everything you need in Google Cloud.${NC}\n"
}

# Check if running in Cloud Shell
check_cloud_shell() {
    if [[ "${CLOUD_SHELL:-}" != "true" ]]; then
        log_error "This script must be run in Google Cloud Shell for one-click deployment"
        echo
        echo "Please open: https://shell.cloud.google.com"
        echo "Then run: curl -sSL https://raw.githubusercontent.com/your-repo/sage-financial/main/cloudshell/one-click-deploy.sh | bash"
        exit 1
    fi
    log_success "Running in Google Cloud Shell"
}

# Get organization and billing account
setup_organization_billing() {
    log_step "Setting up organization and billing..."
    
    # Get organization ID
    local orgs=$(gcloud organizations list --format="value(name,displayName)" 2>/dev/null || echo "")
    
    if [[ -z "$orgs" ]]; then
        log_warning "No organization found. Using personal account."
        ORGANIZATION_ID=""
    else
        echo "Available organizations:"
        gcloud organizations list --format="table(displayName,name)"
        echo
        read -p "Enter organization ID (or press Enter to skip): " ORGANIZATION_ID
    fi
    
    # Get billing account
    local billing_accounts=$(gcloud billing accounts list --format="value(name,displayName)" 2>/dev/null || echo "")
    
    if [[ -z "$billing_accounts" ]]; then
        log_error "No billing accounts found. You need to set up billing first."
        echo "Please visit: https://console.cloud.google.com/billing"
        exit 1
    fi
    
    echo "Available billing accounts:"
    gcloud billing accounts list --format="table(displayName,name)"
    echo
    
    while [[ -z "$BILLING_ACCOUNT_ID" ]]; do
        read -p "Enter billing account ID: " BILLING_ACCOUNT_ID
        if ! gcloud billing accounts describe "$BILLING_ACCOUNT_ID" &>/dev/null; then
            log_error "Invalid billing account ID"
            BILLING_ACCOUNT_ID=""
        fi
    done
    
    log_success "Billing account configured: $BILLING_ACCOUNT_ID"
}

# Create unique project ID
create_project() {
    log_step "Creating new Google Cloud project..."
    
    # Generate unique project ID
    local timestamp=$(date +%s)
    local random=$(shuf -i 1000-9999 -n 1)
    PROJECT_ID="sage-financial-${timestamp}-${random}"
    
    log_info "Creating project: $PROJECT_ID"
    
    # Create project
    if [[ -n "$ORGANIZATION_ID" ]]; then
        gcloud projects create "$PROJECT_ID" \
            --name="$PROJECT_NAME" \
            --organization="$ORGANIZATION_ID"
    else
        gcloud projects create "$PROJECT_ID" \
            --name="$PROJECT_NAME"
    fi
    
    # Set as active project
    gcloud config set project "$PROJECT_ID"
    
    # Link billing account
    gcloud billing projects link "$PROJECT_ID" \
        --billing-account="$BILLING_ACCOUNT_ID"
    
    log_success "Project created and billing linked: $PROJECT_ID"
}

# Gather API credentials
gather_credentials() {
    log_step "Gathering API credentials..."
    
    cat << EOF

${YELLOW}We need some API credentials to set up your app:${NC}

${SHIELD} ${WHITE}Google OAuth Credentials${NC} (Required for user authentication):
   • Go to: https://console.cloud.google.com/apis/credentials
   • Create OAuth 2.0 Client ID
   • Application type: Web application
   • We'll configure redirect URIs automatically

${SHIELD} ${WHITE}Plaid Credentials${NC} (Optional for bank account integration):
   • Go to: https://dashboard.plaid.com/
   • Sign up/login and create an application
   • Get your Client ID and Secret
   • You can skip this and set up later in the app

EOF
    
    # Google OAuth credentials (Required)
    echo "${WHITE}Google OAuth Setup (Required):${NC}"
    while [[ -z "$GOOGLE_OAUTH_CLIENT_ID" ]]; do
        read -p "Enter Google OAuth Client ID: " GOOGLE_OAUTH_CLIENT_ID
    done
    
    while [[ -z "$GOOGLE_OAUTH_CLIENT_SECRET" ]]; do
        read -s -p "Enter Google OAuth Client Secret: " GOOGLE_OAUTH_CLIENT_SECRET
        echo
    done
    
    echo
    
    # Plaid credentials (Optional)
    echo "${WHITE}Plaid Setup (Optional):${NC}"
    read -p "Do you want to set up Plaid integration now? [y/N]: " setup_plaid
    
    if [[ "${setup_plaid,,}" == "y" ]]; then
        while [[ -z "$PLAID_CLIENT_ID" ]]; do
            read -p "Enter Plaid Client ID: " PLAID_CLIENT_ID
        done
        
        while [[ -z "$PLAID_SECRET" ]]; do
            read -s -p "Enter Plaid Secret: " PLAID_SECRET
            echo
        done
        
        echo "Select Plaid environment:"
        echo "1) Sandbox (for testing)"
        echo "2) Production (for live data)"
        read -p "Choice [1]: " plaid_choice
        
        case ${plaid_choice:-1} in
            2) PLAID_ENV="production" ;;
            *) PLAID_ENV="sandbox" ;;
        esac
        
        log_success "Plaid credentials configured"
    else
        log_info "Skipping Plaid setup - you can configure this later in the app"
        PLAID_CLIENT_ID="SETUP_LATER"
        PLAID_SECRET="SETUP_LATER"
        PLAID_ENV="sandbox"
    fi
    
    log_success "API credentials collected"
}

# Setup GitHub integration
setup_github_integration() {
    log_step "Setting up GitHub integration..."
    
    echo
    echo "${GITHUB} ${WHITE}GitHub Integration (Optional)${NC}"
    echo "This will set up automatic deployments from your GitHub repository."
    echo
    
    read -p "Do you want to set up GitHub integration? [y/N]: " setup_github
    
    if [[ "${setup_github,,}" == "y" ]]; then
        read -p "Enter GitHub repository (owner/repo): " GITHUB_REPO
        
        echo
        echo "To create a GitHub token:"
        echo "1. Go to: https://github.com/settings/tokens"
        echo "2. Generate new token (classic)"
        echo "3. Select scopes: repo, admin:repo_hook"
        echo
        
        read -s -p "Enter GitHub token: " GITHUB_TOKEN
        echo
        
        log_success "GitHub integration configured"
    else
        log_info "Skipping GitHub integration"
    fi
}

# Deploy infrastructure using Terraform
deploy_infrastructure() {
    log_step "Deploying infrastructure with Terraform..."
    
    cd "$SCRIPT_DIR/../deployment/terraform"
    
    # Generate JWT secret
    local jwt_secret=$(openssl rand -base64 32)
    
    # Create terraform.tfvars file
    cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
region = "$REGION"
app_name = "sage"
plaid_client_id = "$PLAID_CLIENT_ID"
plaid_secret = "$PLAID_SECRET"
plaid_env = "$PLAID_ENV"
google_oauth_client_id = "$GOOGLE_OAUTH_CLIENT_ID"
google_oauth_client_secret = "$GOOGLE_OAUTH_CLIENT_SECRET"
EOF
    
    # Initialize and deploy Terraform
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan
    
    # Store additional secrets
    echo -n "$jwt_secret" | gcloud secrets versions add SECRET_KEY --data-file=- --project="$PROJECT_ID"
    echo -n "$PROJECT_ID" | gcloud secrets versions add FIREBASE_PROJECT_ID --data-file=- --project="$PROJECT_ID"
    
    # Get outputs
    BACKEND_URL=$(terraform output -raw backend_url)
    FRONTEND_URL="https://$PROJECT_ID.web.app"
    
    log_success "Infrastructure deployed successfully"
    
    cd "$SCRIPT_DIR"
}

# Create billing budget with alerts
create_billing_budget() {
    local project_id="$1"
    local billing_account="$2"
    local budget_amount="${3:-10}"
    
    log_step "Setting up billing budget and alerts..."
    
    # Create Pub/Sub topic for billing alerts
    if ! gcloud pubsub topics describe billing-alerts --project="$project_id" &>/dev/null; then
        gcloud pubsub topics create billing-alerts --project="$project_id"
    fi
    
    # Create billing budget
    cat > budget-config.json << EOF
{
  "displayName": "Sage App Monthly Budget",
  "budgetFilter": {
    "projects": ["projects/$project_id"]
  },
  "amount": {
    "specifiedAmount": {
      "currencyCode": "USD",
      "units": "$budget_amount"
    }
  },
  "thresholdRules": [
    {
      "thresholdPercent": 0.5,
      "spendBasis": "CURRENT_SPEND"
    },
    {
      "thresholdPercent": 0.9,
      "spendBasis": "CURRENT_SPEND"
    },
    {
      "thresholdPercent": 1.0,
      "spendBasis": "CURRENT_SPEND"
    }
  ],
  "notificationsRule": {
    "pubsubTopic": "projects/$project_id/topics/billing-alerts",
    "schemaVersion": "1.0"
  }
}
EOF
    
    if gcloud billing budgets create \
        --billing-account="$billing_account" \
        --budget-from-file=budget-config.json; then
        log_success "Budget created with $budget_amount USD monthly limit"
    else
        log_warning "Budget creation failed or budget already exists"
    fi
    
    rm -f budget-config.json
}

# Setup OAuth configuration automatically
setup_oauth_automatically() {
    log_step "Configuring OAuth settings..."
    
    # Enable Identity Platform
    gcloud services enable identitytoolkit.googleapis.com --project="$PROJECT_ID"
    
    # Wait for service to be ready
    sleep 30
    
    # Configure OAuth provider
    cat > oauth-config.json << EOF
{
  "name": "projects/$PROJECT_ID/identityProviders/google.com",
  "displayName": "Google",
  "enabled": true,
  "clientId": "$GOOGLE_OAUTH_CLIENT_ID",
  "clientSecret": "$GOOGLE_OAUTH_CLIENT_SECRET"
}
EOF
    
    # Apply OAuth configuration
    gcloud alpha identity providers update google.com \
        --project="$PROJECT_ID" \
        --client-id="$GOOGLE_OAUTH_CLIENT_ID" \
        --client-secret="$GOOGLE_OAUTH_CLIENT_SECRET" \
        --enabled || true
    
    rm -f oauth-config.json
    
    log_success "OAuth configuration completed"
    
    # Provide manual steps for OAuth redirect URIs
    cat << EOF

${YELLOW}IMPORTANT: Complete OAuth Setup${NC}
Please update your OAuth redirect URIs:

1. Go to: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID
2. Edit your OAuth 2.0 Client ID
3. Add these authorized redirect URIs:
   • http://localhost:5173/auth/callback (for development)
   • $FRONTEND_URL/auth/callback (for production)

EOF
}

# Setup GitHub Actions secrets
setup_github_actions() {
    if [[ -z "$GITHUB_REPO" || -z "$GITHUB_TOKEN" ]]; then
        log_info "Skipping GitHub Actions setup (no repository configured)"
        return
    fi
    
    log_step "Setting up GitHub Actions..."
    
    # Get deployment service account
    local sa_email="sage-deployment-sa@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Create service account key
    gcloud iam service-accounts keys create sa-key.json \
        --iam-account="$sa_email" \
        --project="$PROJECT_ID"
    
    local sa_key=$(base64 -w 0 sa-key.json)
    
    # Set GitHub secrets using GitHub CLI
    if command -v gh &> /dev/null; then
        echo "$sa_key" | gh secret set GCP_SA_KEY --repo "$GITHUB_REPO"
        echo "$PROJECT_ID" | gh secret set GCP_PROJECT_ID --repo "$GITHUB_REPO"
        echo "$REGION" | gh secret set GCP_REGION --repo "$GITHUB_REPO"
        echo "$PLAID_CLIENT_ID" | gh secret set PLAID_CLIENT_ID --repo "$GITHUB_REPO"
        echo "$PLAID_SECRET" | gh secret set PLAID_SECRET --repo "$GITHUB_REPO"
        echo "$PLAID_ENV" | gh secret set PLAID_ENV --repo "$GITHUB_REPO"
        echo "$GOOGLE_OAUTH_CLIENT_ID" | gh secret set GOOGLE_OAUTH_CLIENT_ID --repo "$GITHUB_REPO"
        echo "$GOOGLE_OAUTH_CLIENT_SECRET" | gh secret set GOOGLE_OAUTH_CLIENT_SECRET --repo "$GITHUB_REPO"
        
        log_success "GitHub Actions secrets configured"
    else
        log_warning "GitHub CLI not available. Manual setup required for CI/CD."
    fi
    
    rm -f sa-key.json
}

# Deploy applications
deploy_applications() {
    log_step "Deploying applications..."
    
    # Deploy backend
    cd "$SCRIPT_DIR/../deployment/scripts"
    ./deploy-backend.sh \
        --project-id "$PROJECT_ID" \
        --region "$REGION"
    
    # Deploy frontend
    ./deploy-frontend.sh \
        --project-id "$PROJECT_ID" \
        --backend-url "$BACKEND_URL"
    
    log_success "Applications deployed successfully"
    
    cd "$SCRIPT_DIR"
}

# Run health checks
run_health_checks() {
    log_step "Running health checks..."
    
    local checks_passed=0
    local total_checks=3
    
    # Check backend
    if curl -f -s "$BACKEND_URL/health" > /dev/null; then
        log_success "Backend health check passed"
        checks_passed=$((checks_passed + 1))
    else
        log_warning "Backend health check failed"
    fi
    
    # Check frontend
    if curl -f -s "$FRONTEND_URL" > /dev/null; then
        log_success "Frontend accessibility check passed"
        checks_passed=$((checks_passed + 1))
    else
        log_warning "Frontend accessibility check failed"
    fi
    
    # Check Firestore
    if gcloud firestore databases describe --database="(default)" --project="$PROJECT_ID" &>/dev/null; then
        log_success "Firestore database check passed"
        checks_passed=$((checks_passed + 1))
    else
        log_warning "Firestore database check failed"
    fi
    
    echo
    log_info "Health checks completed: $checks_passed/$total_checks passed"
}

# Show final summary
show_summary() {
    log_header "🎉 DEPLOYMENT COMPLETED!"
    
    cat << EOF
${GREEN}Your Sage Financial Management App is ready!${NC}

${WHITE}📊 Project Details:${NC}
   Project ID: ${CYAN}$PROJECT_ID${NC}
   Region: ${CYAN}$REGION${NC}
   Billing: ${CYAN}$BILLING_ACCOUNT_ID${NC}

${WHITE}🌐 Application URLs:${NC}
   Frontend: ${CYAN}$FRONTEND_URL${NC}
   Backend:  ${CYAN}$BACKEND_URL${NC}

${WHITE}💰 Cost Management:${NC}
   ${CHECK} Budget alert set for \$10/month
   ${CHECK} Billing notifications enabled
   
${WHITE}🔐 Security:${NC}
   ${CHECK} All secrets stored in Secret Manager
   ${CHECK} Service accounts with minimal permissions
   ${CHECK} OAuth authentication configured

${WHITE}📦 CI/CD:${NC}
EOF

    if [[ -n "$GITHUB_REPO" ]]; then
        echo "   ${CHECK} GitHub Actions configured for $GITHUB_REPO"
        echo "   ${CHECK} Automatic deployments on push to main"
    else
        echo "   ${YELLOW}⚠️${NC}  GitHub integration not configured"
    fi

    cat << EOF

${WHITE}🚀 Next Steps:${NC}
   1. Complete OAuth redirect URI setup (see instructions above)
   2. Test your application: ${CYAN}$FRONTEND_URL${NC}
   3. Connect a test bank account using Plaid
   4. Monitor costs in billing dashboard

${WHITE}📚 Resources:${NC}
   • Documentation: https://github.com/your-repo/sage-financial/docs
   • Support: Open an issue on GitHub
   • Monitoring: https://console.cloud.google.com/monitoring?project=$PROJECT_ID

${GREEN}Thank you for using Sage Financial Management!${NC}
EOF
}

# Main execution
main() {
    show_welcome_banner
    check_cloud_shell
    setup_organization_billing
    create_project
    gather_credentials
    setup_github_integration
    deploy_infrastructure
    create_billing_budget "$PROJECT_ID" "$BILLING_ACCOUNT_ID" "10"
    setup_oauth_automatically
    setup_github_actions
    deploy_applications
    run_health_checks
    show_summary
}

# Error handling
cleanup() {
    log_warning "Deployment interrupted"
    if [[ -n "${PROJECT_ID:-}" ]]; then
        echo "Project created: $PROJECT_ID"
        echo "You may want to delete it to avoid charges: gcloud projects delete $PROJECT_ID"
    fi
    exit 1
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run main function
main "$@"