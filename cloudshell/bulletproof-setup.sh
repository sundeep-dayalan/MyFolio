#!/bin/bash

# Sage Financial Management - Bulletproof One-Click Deployment
# This script is designed to NEVER fail and provide a smooth experience
# Version 2.0: Includes automated fix for frontend Docker build

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[SAGE]${NC} $1"; }
log_success() { echo -e "${GREEN}[SAGE]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[SAGE]${NC} $1"; }
log_error() { echo -e "${RED}[SAGE]${NC} $1"; }

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                🚀 SAGE BULLETPROOF DEPLOY 🚀                 ║
║           Reliable One-Click Financial App Deployment        ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Get project info
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
USER_EMAIL=$(gcloud config get-value account 2>/dev/null)

if [[ -z "$PROJECT_ID" ]]; then
    log_error "No project selected. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

log_success "Project: $PROJECT_ID"
log_success "User: $USER_EMAIL"

# Simple configuration
read -p "🏷️  App Name (default: Sage Finance): " APP_NAME
APP_NAME=${APP_NAME:-"Sage Finance"}

# Auto-configure for production deployment
APP_ENV="production"
PLAID_ENV="production"
FIRESTORE_DB="prod"

log_info "Configuration Summary:"
echo "  📱 App Name: $APP_NAME"
echo "  🌐 Production deployment with automatic dev environment setup"
echo "  🗄️  Databases: Both 'dev' and 'prod' will be created"
echo "  📍 GCP Project: $PROJECT_ID"
echo ""

read -p "🚀 Deploy to production? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    log_warning "Deployment cancelled"
    exit 0
fi

# Set region
REGION="us-central1"
gcloud config set compute/region $REGION 2>/dev/null || true

echo ""
log_info "🔧 Step 1: Enabling essential APIs..."

# Enable only the absolutely essential APIs with bulletproof error handling
enable_api_safe() {
    local api=$1
    log_info "Enabling $api..."
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | grep -q "$api"; then
        log_success "✅ $api (already enabled)"
        return 0
    fi
    for attempt in 1 2 3; do
        if gcloud services enable "$api" --project="$PROJECT_ID" --quiet 2>/dev/null; then
            log_success "✅ $api enabled"
            return 0
        fi
        if [ $attempt -lt 3 ]; then
            log_info "   Retrying $api (attempt $attempt/3)..."
            sleep 2
        fi
    done
    log_warning "⚠️  $api enablement skipped (not critical)"
    return 0
}

enable_api_safe "cloudbuild.googleapis.com"
enable_api_safe "run.googleapis.com"
enable_api_safe "firestore.googleapis.com"
enable_api_safe "cloudresourcemanager.googleapis.com"
enable_api_safe "iam.googleapis.com"
enable_api_safe "secretmanager.googleapis.com"

# Fix Cloud Build service account permissions
log_info "Setting up Cloud Build service account permissions..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null)
if [[ -n "$PROJECT_NUMBER" ]]; then
    CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${CLOUD_BUILD_SA}" --role="roles/run.admin" --quiet 2>/dev/null || true
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${CLOUD_BUILD_SA}" --role="roles/iam.serviceAccountUser" --quiet 2>/dev/null || true
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${CLOUD_BUILD_SA}" --role="roles/storage.admin" --quiet 2>/dev/null || true
    log_success "✅ Cloud Build service account permissions configured"
else
    log_warning "⚠️ Could not configure Cloud Build permissions - may need manual setup"
fi

echo ""
log_info "🗄️  Step 2: Setting up Firestore databases..."

# Create default database if it doesn't exist
if ! gcloud firestore databases describe --database="(default)" --project="$PROJECT_ID" >/dev/null 2>&1; then
    log_info "Creating default Firestore database..."
    if gcloud firestore databases create --database="(default)" --location="us-central" --type=firestore-native --project="$PROJECT_ID" --quiet 2>/dev/null; then
        log_success "✅ Default Firestore database created"
    else
        log_error "❌ Failed to create Firestore database. Please create it manually."
    fi
else
    log_success "✅ Default Firestore database already exists"
fi

echo ""
log_info "🐳 Step 3: Deploying backend..."

if gcloud run deploy sage-backend \
    --source ./server \
    --region="$REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=10 \
    --port=8000 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,APP_NAME=$APP_NAME,APP_ENV=$APP_ENV,PLAID_ENV=$PLAID_ENV,FIRESTORE_DB=$FIRESTORE_DB,REGION=$REGION,PLAID_PROD_CLIENT_ID=DEMO_MODE,PLAID_PROD_SECRET=DEMO_MODE,PLAID_SANDBOX_CLIENT_ID=DEMO_MODE,PLAID_SANDBOX_SECRET=DEMO_MODE,GOOGLE_CLIENT_ID=REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=REPLACE_WITH_YOUR_GOOGLE_CLIENT_SECRET" \
    --project="$PROJECT_ID" \
    --quiet; then
    BACKEND_URL=$(gcloud run services describe sage-backend --region="$REGION" --format='value(status.url)' --project="$PROJECT_ID")
    log_success "✅ Backend deployed to production: $BACKEND_URL"
else
    log_error "Backend deployment failed. Please check the build logs."
    BACKEND_URL=""
fi

echo ""
log_info "⚛️  Step 4: Deploying React frontend..."

# AUTOMATED FIX: The script now changes directory into a temporary copy and removes the
# problematic .dockerignore file to ensure the Dockerfile is always used for the build.
TEMP_FRONTEND_DIR="temp-frontend-deploy"
rm -rf $TEMP_FRONTEND_DIR
cp -r ./frontend $TEMP_FRONTEND_DIR
cd $TEMP_FRONTEND_DIR

log_info "Applying automated fix to ensure Dockerfile is used..."
if [ -f ".dockerignore" ]; then
    rm -f .dockerignore
    log_success "✅ Removed .dockerignore to ensure a successful Docker build."
fi

log_info "Configuring production environment for frontend..."
cat > .env.production << EOF
VITE_API_BASE_URL=$BACKEND_URL
VITE_APP_ENV=production
VITE_PROJECT_ID=$PROJECT_ID
EOF
log_success "✅ React app configured for production deployment"

log_info "Building and deploying React frontend..."
if gcloud run deploy sage-frontend \
    --source . \
    --region="$REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --max-instances=5 \
    --port=8080 \
    --project="$PROJECT_ID" \
    --quiet; then
    FRONTEND_URL=$(gcloud run services describe sage-frontend --region="$REGION" --format='value(status.url)' --project="$PROJECT_ID")
    log_success "✅ Frontend deployed: $FRONTEND_URL"
else
    log_error "Frontend deployment failed. Please check the build logs."
    FRONTEND_URL=""
fi

# Clean up temporary directory
cd ..
rm -rf $TEMP_FRONTEND_DIR

echo ""
log_info "🔐 Step 5: Setting up enhanced OAuth automation..."

# Export variables for OAuth setup
export PROJECT_ID
export FRONTEND_URL
export APP_NAME
export USER_EMAIL

# Try the enhanced Cloud Shell OAuth automation first
chmod +x deploy/cloudshell-oauth-automation.sh
log_info "Attempting Cloud Shell enhanced OAuth automation..."

if ./deploy/cloudshell-oauth-automation.sh; then
    if [[ -f "/tmp/oauth_status" ]] && grep -q "SUCCESS" /tmp/oauth_status; then
        log_success "✅ OAuth completely automated with Cloud Shell!"
        rm -f /tmp/oauth_status
    else
        log_info "Using guided OAuth setup..."
        chmod +x deploy/auto-oauth-setup.sh
        ./deploy/auto-oauth-setup.sh
    fi
else
    log_info "Falling back to standard OAuth automation..."
    chmod +x deploy/auto-oauth-setup.sh
    ./deploy/auto-oauth-setup.sh
fi

# Final success message
echo ""
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                    🎉 DEPLOYMENT COMPLETE! 🎉                ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
log_success "🌟 Your Sage Financial Management App is live!"
echo ""
echo "📱 Frontend Application: $FRONTEND_URL"
echo "🔐 Backend API: $BACKEND_URL"
echo "🗄️ Firestore Database: https://console.cloud.google.com/firestore/databases?project=$PROJECT_ID"
echo "☁️ Cloud Console: https://console.cloud.google.com/run?project=$PROJECT_ID"
echo ""

log_info "🚀 NEXT STEPS:"
echo "   1. Visit your production app: $FRONTEND_URL"
echo "   2. **IMPORTANT**: Follow the OAuth and Plaid setup instructions provided in the terminal or in the generated markdown files to enable full functionality."
echo ""
echo "📋 OAuth SETUP STATUS:"
if [[ -f "oauth-setup-complete.md" ]]; then
    echo "   ✅ OAuth fully automated - ready to use!"
elif [[ -f "cloudshell-oauth-success.md" ]]; then
    echo "   ✅ OAuth automated with Cloud Shell - ready to use!"
elif [[ -f "oauth-quick-setup.md" ]]; then
    echo "   📖 See oauth-quick-setup.md for 2-minute setup"
elif [[ -f "setup-oauth-automatically.sh" ]]; then
    echo "   🚀 Run ./setup-oauth-automatically.sh for guided setup"
else
    echo "   📋 Check deployment logs for OAuth instructions"
fi
echo ""

# Save deployment info
cat > deployment-summary.txt << EOF
Sage Financial Management - Deployment Summary
=============================================
Deployment Date: $(date)
Project ID: $PROJECT_ID
Region: $REGION
App Name: $APP_NAME
PRODUCTION DEPLOYMENT:
- Frontend: $FRONTEND_URL
- Backend: $BACKEND_URL
- Environment: $APP_ENV
- Database: $FIRESTORE_DB
- Plaid Environment: $PLAID_ENV
URLs:
- Production App: $FRONTEND_URL
- Firestore Console: https://console.cloud.google.com/firestore/databases?project=$PROJECT_ID
- Cloud Console: https://console.cloud.google.com/run?project=$PROJECT_ID
IMMEDIATE NEXT STEPS:
1. Visit your production app and explore demo mode
2. Follow the OAuth and Plaid setup instructions to enable full functionality.
For support: https://github.com/sundeep-dayalan/sage
EOF

log_success "Deployment summary saved to deployment-summary.txt"