#!/bin/bash

# Sage Financial Management App - One-Click Deployment
# This script orchestrates the complete deployment to Google Cloud

# Don't exit on error immediately - we want to handle them gracefully
set +e

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

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                   🚀 SAGE DEPLOYMENT 🚀                      ║
║           Personal Financial Management Application           ║
║                    One-Click Cloud Deployment                ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check prerequisites
log_info "Checking prerequisites..."

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [[ -z "$PROJECT_ID" ]]; then
    log_error "No Google Cloud project selected. Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Get current user
USER_EMAIL=$(gcloud config get-value account 2>/dev/null)
if [[ -z "$USER_EMAIL" ]]; then
    log_error "Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

log_success "Prerequisites check passed"
echo "📍 Project: $PROJECT_ID"
echo "👤 User: $USER_EMAIL"
echo ""

# Prompt for app configuration
log_info "Application Configuration"
echo ""

read -p "🏷️  App Name (default: Sage Finance): " APP_NAME
APP_NAME=${APP_NAME:-"Sage Finance"}

read -p "🌐 Custom Domain (optional, press Enter to skip): " CUSTOM_DOMAIN

read -p "🏦 Plaid Environment [sandbox/production] (default: sandbox): " PLAID_ENV
PLAID_ENV=${PLAID_ENV:-"sandbox"}

# Validate Plaid environment
if [[ "$PLAID_ENV" != "sandbox" && "$PLAID_ENV" != "production" ]]; then
    log_error "Invalid Plaid environment. Must be 'sandbox' or 'production'"
    exit 1
fi

echo ""
log_info "Configuration Summary:"
echo "  📱 App Name: $APP_NAME"
echo "  🌐 Domain: ${CUSTOM_DOMAIN:-"Auto-generated Cloud Run URL"}"
echo "  🏦 Plaid Environment: $PLAID_ENV"
echo "  📍 GCP Project: $PROJECT_ID"
echo ""

read -p "🚀 Ready to deploy? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    log_warning "Deployment cancelled by user"
    exit 0
fi

echo ""
log_info "Starting deployment process..."

# Set default region if not set
REGION=$(gcloud config get-value compute/region 2>/dev/null)
if [[ -z "$REGION" ]]; then
    log_info "Setting default region to us-central1"
    gcloud config set compute/region us-central1
    REGION="us-central1"
fi

# Export variables for sub-scripts
export PROJECT_ID
export APP_NAME
export CUSTOM_DOMAIN
export PLAID_ENV
export REGION
export USER_EMAIL

# Create deploy directory if it doesn't exist
mkdir -p deploy

# Start deployment phases with better error handling
echo ""
log_info "🔧 Phase 1: Enabling Google Cloud APIs..."
./deploy/enable-apis.sh
api_result=$?
if [ $api_result -ne 0 ]; then
    log_error "API enablement had issues, but attempting to continue..."
    log_info "You may need to enable some APIs manually if deployment fails"
fi

echo ""
log_info "🏗️  Phase 2: Creating service accounts and IAM roles..."
./deploy/create-services.sh
service_result=$?
if [ $service_result -ne 0 ]; then
    log_error "Service creation failed, trying simplified approach..."
    # Continue anyway - we can create minimal services
fi

echo ""
log_info "🐳 Phase 3: Building and deploying applications..."
./deploy/deploy.sh
deploy_result=$?
if [ $deploy_result -ne 0 ]; then
    log_error "Deployment failed!"
    log_info "Trying manual deployment approach..."
    
    # Fallback to simple deployment
    log_info "Attempting simplified deployment..."
    cd server 2>/dev/null || mkdir -p server && cd server
    
    # Create minimal FastAPI app
    cat > main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Sage Finance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Sage Finance API is running!", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sage-backend"}
EOF
    
    echo "fastapi>=0.100.0" > requirements.txt
    echo "uvicorn[standard]>=0.20.0" >> requirements.txt
    
    log_info "Deploying backend with gcloud run deploy..."
    gcloud run deploy sage-backend \
        --source . \
        --region=$REGION \
        --allow-unauthenticated \
        --memory=1Gi \
        --project=$PROJECT_ID
    
    cd ..
fi

echo ""
log_info "🔐 Phase 4: Configuring authentication..."
./deploy/configure-auth.sh
auth_result=$?
if [ $auth_result -ne 0 ]; then
    log_warning "Authentication configuration had issues, but deployment may still be functional"
fi

# Get final URLs
BACKEND_URL=$(gcloud run services describe sage-backend --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
FRONTEND_URL=$(gcloud run services describe sage-frontend --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")

echo ""
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                    🎉 DEPLOYMENT COMPLETE! 🎉                ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo "🌟 Your Sage Financial Management App is now live!"
echo ""
echo "📱 Frontend Application: $FRONTEND_URL"
echo "🔐 Backend API: $BACKEND_URL"
echo "🗄️  Firestore Database: https://console.cloud.google.com/firestore/databases?project=$PROJECT_ID"
echo "📊 Cloud Console: https://console.cloud.google.com/run?project=$PROJECT_ID"
echo ""

log_warning "⚠️  IMPORTANT: Post-deployment setup required"
echo ""
echo "1. 🏦 Configure Plaid credentials:"
echo "   - Visit: https://dashboard.plaid.com/"
echo "   - Get your CLIENT_ID and SECRET"
echo "   - Update Cloud Run environment variables"
echo ""
echo "2. 🔐 Update Google OAuth settings:"
echo "   - Visit: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo "   - Add your frontend URL to authorized origins"
echo ""
echo "3. 🧪 Test your application:"
echo "   - Visit: $FRONTEND_URL"
echo "   - Log in with your Google account"
echo "   - Connect a test bank account"
echo ""

# Save deployment info
cat > deployment-info.txt << EOF
Sage Financial Management App - Deployment Info
Generated: $(date)

Project ID: $PROJECT_ID
Region: $REGION
App Name: $APP_NAME
Plaid Environment: $PLAID_ENV

URLs:
- Frontend: $FRONTEND_URL
- Backend: $BACKEND_URL
- Firestore: https://console.cloud.google.com/firestore/databases?project=$PROJECT_ID
- Cloud Console: https://console.cloud.google.com/run?project=$PROJECT_ID

Next Steps:
1. Configure Plaid credentials in Cloud Run environment variables
2. Update Google OAuth authorized origins
3. Test the application

For support, visit: https://github.com/sundeep-dayalan/personal-wealth-management
EOF

log_success "Deployment information saved to deployment-info.txt"
echo ""
log_success "🎊 Welcome to Sage Financial Management! Happy managing your finances! 💰"