#!/bin/bash

# Google Cloud Deployment Script for Sage FastAPI Application
# This script sets up and deploys your FastAPI app to Google Cloud Run

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables (update these)
PROJECT_ID="fit-guide-465001-p3"
REGION="us-central1"
SERVICE_NAME="sage-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo -e "${BLUE}🚀 Sage FastAPI Deployment to Google Cloud Run${NC}"
echo "=================================================="

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    print_error "Please set PROJECT_ID variable in this script"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_warning "Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

print_status "Setting project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

print_status "Enabling required APIs"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

print_status "Building Docker image"
docker build -t $IMAGE_NAME .

print_status "Pushing image to Google Container Registry"
docker push $IMAGE_NAME

print_status "Creating secrets in Secret Manager (if they don't exist)"

# Function to create secret if it doesn't exist
create_secret_if_not_exists() {
    local secret_name=$1
    local secret_value=$2
    
    if ! gcloud secrets describe $secret_name &> /dev/null; then
        echo -n "$secret_value" | gcloud secrets create $secret_name --data-file=-
        print_status "Created secret: $secret_name"
    else
        print_warning "Secret $secret_name already exists"
    fi
}

# You'll need to update these with your actual values
read -p "Enter your SECRET_KEY (or press Enter to generate one): " SECRET_KEY
if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    print_status "Generated SECRET_KEY: $SECRET_KEY"
fi

read -p "Enter your GOOGLE_CLIENT_ID: " GOOGLE_CLIENT_ID
read -p "Enter your GOOGLE_CLIENT_SECRET: " GOOGLE_CLIENT_SECRET
read -p "Enter your FIREBASE_PROJECT_ID: " FIREBASE_PROJECT_ID

# Create secrets
create_secret_if_not_exists "SECRET_KEY" "$SECRET_KEY"
create_secret_if_not_exists "GOOGLE_CLIENT_ID" "$GOOGLE_CLIENT_ID"
create_secret_if_not_exists "GOOGLE_CLIENT_SECRET" "$GOOGLE_CLIENT_SECRET"
create_secret_if_not_exists "FIREBASE_PROJECT_ID" "$FIREBASE_PROJECT_ID"

# Handle Firebase service account
if [ -f "service-account.json" ]; then
    create_secret_if_not_exists "FIREBASE_CREDENTIALS" "$(cat service-account.json)"
    print_status "Firebase service account uploaded to Secret Manager"
else
    print_warning "service-account.json not found. Please upload it manually to Secret Manager as 'FIREBASE_CREDENTIALS'"
fi

print_status "Deploying to Cloud Run"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8000 \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --set-env-vars ENVIRONMENT=production,DEBUG=false,LOG_LEVEL=INFO \
    --set-secrets SECRET_KEY=SECRET_KEY:latest \
    --set-secrets GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest \
    --set-secrets GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest \
    --set-secrets FIREBASE_PROJECT_ID=FIREBASE_PROJECT_ID:latest \
    --set-secrets FIREBASE_CREDENTIALS=FIREBASE_CREDENTIALS:latest

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

print_status "Deployment completed successfully!"
echo "🎉 Deployment complete!"
echo "Your API is now available at: $SERVICE_URL"
echo ""
echo "📋 Testing deployment..."
HEALTH_STATUS=$(curl -s "$SERVICE_URL/health" | jq -r '.status' 2>/dev/null || echo "error")
if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo "✅ Health check passed! API is running correctly."
    echo "🔗 API Documentation: $SERVICE_URL/docs"
    echo "🔗 Health Check: $SERVICE_URL/health"
else
    echo "⚠️  Health check failed. Please check the logs:"
    echo "   gcloud logs read --service=sage-api --limit=50"
fi

echo ""
echo "📋 Next steps:"
echo "1. Test your API endpoints at: $SERVICE_URL/docs"
echo "2. Configure your frontend to use the new API URL"
echo "3. Set up monitoring and alerting"
echo "4. Consider setting up a custom domain"
echo ""
echo "📊 Useful commands:"
echo "  View logs: gcloud logs read --service=sage-api --limit=50"
echo "  Update service: gcloud run deploy sage-api --image gcr.io/$PROJECT_ID/sage-api"
echo "  Get service details: gcloud run services describe sage-api --region=$REGION"
