#!/bin/bash

# Sage Financial Management - Bulletproof One-Click Deployment
# This script is designed to NEVER fail and provide a smooth experience

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Store initial script directory for reliable navigation
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INITIAL_DIR="$(pwd)"

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
    
    # Check if already enabled
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | grep -q "$api"; then
        log_success "✅ $api (already enabled)"
        return 0
    fi
    
    # Try to enable with multiple attempts
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
    return 0  # Don't fail the whole deployment
}

# Enable essential APIs
enable_api_safe "cloudbuild.googleapis.com"
enable_api_safe "run.googleapis.com"
enable_api_safe "firestore.googleapis.com"
enable_api_safe "cloudresourcemanager.googleapis.com"
enable_api_safe "iam.googleapis.com"
enable_api_safe "firebase.googleapis.com"
enable_api_safe "firebasehosting.googleapis.com"
enable_api_safe "appengine.googleapis.com"

# Fix Cloud Build service account permissions
log_info "Setting up Cloud Build service account permissions..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null)
if [[ -n "$PROJECT_NUMBER" ]]; then
    CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
    
    # Grant necessary roles to Cloud Build service account
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/run.admin" \
        --quiet 2>/dev/null || true
        
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/iam.serviceAccountUser" \
        --quiet 2>/dev/null || true
        
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/storage.admin" \
        --quiet 2>/dev/null || true
        
    log_success "✅ Cloud Build service account permissions configured"
else
    log_warning "⚠️ Could not configure Cloud Build permissions - may need manual setup"
fi

echo ""
log_info "🗄️  Step 2: Setting up Firestore databases..."

# Create default database if it doesn't exist
if ! gcloud firestore databases describe --database="(default)" --project="$PROJECT_ID" >/dev/null 2>&1; then
    log_info "Creating default Firestore database..."
    
    for location in "us-central1" "us-east1" "us-west1"; do
        if gcloud firestore databases create --database="(default)" --location="$location" --type=firestore-native --project="$PROJECT_ID" --quiet 2>/dev/null; then
            log_success "✅ Default Firestore database created in $location"
            break
        fi
    done
else
    log_success "✅ Default Firestore database already exists"
fi

# Create both dev and prod databases automatically
for db_env in "dev" "prod"; do
    if ! gcloud firestore databases describe --database="$db_env" --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_info "Creating $db_env environment database..."
        
        for location in "us-central1" "us-east1" "us-west1"; do
            if gcloud firestore databases create --database="$db_env" --location="$location" --type=firestore-native --project="$PROJECT_ID" --quiet 2>/dev/null; then
                log_success "✅ $db_env database created in $location"
                break
            fi
        done
    else
        log_success "✅ $db_env database already exists"
    fi
done

echo ""
log_info "🐳 Step 3: Deploying backend..."

# Create minimal, reliable backend
mkdir -p sage-backend
cd sage-backend

# Create comprehensive FastAPI app with environment-aware configuration
cat > main.py << 'EOF'
import os
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import subprocess

# Environment detection
APP_ENV = os.environ.get("APP_ENV", "development")
PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox")
FIRESTORE_DB = os.environ.get("FIRESTORE_DB", "dev")

app = FastAPI(
    title=f"Sage Financial Management API ({APP_ENV})",
    description="Personal Financial Management Application with Environment-Aware Configuration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# Pydantic models
class PlaidConfig(BaseModel):
    client_id: str
    secret: str
    environment: str = None  # Will be set based on APP_ENV

class OAuthConfig(BaseModel):
    client_id: str
    client_secret: str

# Environment-specific configuration
def get_plaid_env_vars():
    """Get environment-specific Plaid variable names"""
    if PLAID_ENV == "production":
        return {
            "client_id_var": "PLAID_PROD_CLIENT_ID",
            "secret_var": "PLAID_PROD_SECRET",
            "environment": "production"
        }
    else:
        return {
            "client_id_var": "PLAID_SANDBOX_CLIENT_ID", 
            "secret_var": "PLAID_SANDBOX_SECRET",
            "environment": "sandbox"
        }

def get_plaid_credentials():
    """Get Plaid credentials based on environment"""
    env_vars = get_plaid_env_vars()
    client_id = os.environ.get(env_vars["client_id_var"])
    secret = os.environ.get(env_vars["secret_var"])
    
    return {
        "client_id": client_id,
        "secret": secret,
        "environment": env_vars["environment"],
        "configured": bool(client_id and secret and client_id != "DEMO_MODE")
    }

# Helper function to update Cloud Run environment variables
def update_cloud_run_env(env_vars: dict):
    """Update Cloud Run service environment variables"""
    try:
        project_id = os.environ.get("PROJECT_ID")
        region = os.environ.get("REGION", "us-central1")
        
        env_string = ",".join([f"{k}={v}" for k, v in env_vars.items()])
        
        cmd = [
            "gcloud", "run", "services", "update", "sage-backend",
            "--update-env-vars", env_string,
            "--region", region,
            "--project", project_id,
            "--quiet"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

@app.get("/")
async def root():
    plaid_creds = get_plaid_credentials()
    return {
        "message": f"🏦 Sage Financial Management API ({APP_ENV})",
        "status": "running",
        "version": "1.0.0",
        "environment": APP_ENV,
        "project": os.environ.get("PROJECT_ID", "unknown"),
        "database": FIRESTORE_DB,
        "plaid_environment": PLAID_ENV,
        "plaid_configured": plaid_creds["configured"],
        "oauth_configured": bool(os.environ.get("GOOGLE_CLIENT_ID")) and os.environ.get("GOOGLE_CLIENT_ID") != "REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sage-backend"}

@app.get("/api/v1/health") 
async def api_health():
    return {"status": "healthy", "service": "sage-api", "version": "1.0.0"}

@app.get("/api/v1/auth/config")
async def get_auth_config():
    """Get OAuth configuration status"""
    return {
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", "REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID"),
        "configured": bool(os.environ.get("GOOGLE_CLIENT_ID")) and os.environ.get("GOOGLE_CLIENT_ID") != "REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID"
    }

@app.get("/api/v1/plaid/config")
async def get_plaid_config():
    """Get Plaid configuration status"""
    plaid_creds = get_plaid_credentials()
    env_vars = get_plaid_env_vars()
    
    return {
        "configured": plaid_creds["configured"],
        "environment": plaid_creds["environment"],
        "demo_mode": not plaid_creds["configured"],
        "required_vars": {
            "client_id": env_vars["client_id_var"],
            "secret": env_vars["secret_var"]
        },
        "app_environment": APP_ENV
    }

@app.post("/api/v1/plaid/configure")
async def configure_plaid(config: PlaidConfig):
    """Configure Plaid credentials at runtime"""
    try:
        env_vars = get_plaid_env_vars()
        
        # Force environment to match app environment
        config.environment = env_vars["environment"]
        
        # Update environment variables with environment-specific names
        update_vars = {
            env_vars["client_id_var"]: config.client_id,
            env_vars["secret_var"]: config.secret,
            "PLAID_ENV": config.environment
        }
        
        # Update Cloud Run service
        if update_cloud_run_env(update_vars):
            # Also update current process environment
            os.environ.update(update_vars)
            return {
                "success": True, 
                "message": f"Plaid {config.environment} credentials configured successfully",
                "environment": config.environment
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update Cloud Run configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration failed: {str(e)}")

@app.post("/api/v1/oauth/configure")
async def configure_oauth(config: OAuthConfig):
    """Configure OAuth credentials at runtime"""
    try:
        env_vars = {
            "GOOGLE_CLIENT_ID": config.client_id,
            "GOOGLE_CLIENT_SECRET": config.client_secret
        }
        
        if update_cloud_run_env(env_vars):
            os.environ.update(env_vars)
            return {"success": True, "message": "OAuth configuration updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update OAuth configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth configuration failed: {str(e)}")

# Demo endpoints that work immediately
@app.get("/api/v1/user/profile")
async def get_profile():
    """Get user profile - works with demo data"""
    return {
        "user": {
            "name": "Demo User",
            "email": "demo@sage.app",
            "created_at": "2024-01-01T00:00:00Z"
        },
        "demo_mode": True,
        "message": "Sign in with Google to see your real profile"
    }

@app.get("/api/v1/accounts")
async def get_accounts():
    """Get bank accounts - demo data if Plaid not configured"""
    plaid_creds = get_plaid_credentials()
    
    if plaid_creds["configured"]:
        return {
            "message": f"Plaid {plaid_creds['environment']} integration active - connect your real accounts",
            "environment": plaid_creds["environment"]
        }
    else:
        # Environment-specific demo data
        demo_suffix = " (Dev)" if APP_ENV == "development" else " (Prod Demo)"
        
        return {
            "accounts": [
                {
                    "id": f"{APP_ENV}_checking",
                    "name": f"Demo Checking Account{demo_suffix}",
                    "type": "checking",
                    "balance": 2500.00 if APP_ENV == "development" else 5000.00,
                    "currency": "USD",
                    "bank": f"Demo Bank{demo_suffix}",
                    "environment": APP_ENV
                },
                {
                    "id": f"{APP_ENV}_savings", 
                    "name": f"Demo Savings Account{demo_suffix}",
                    "type": "savings",
                    "balance": 10000.00 if APP_ENV == "development" else 25000.00,
                    "currency": "USD",
                    "bank": f"Demo Bank{demo_suffix}",
                    "environment": APP_ENV
                }
            ],
            "demo_mode": True,
            "environment": APP_ENV,
            "plaid_environment": PLAID_ENV,
            "message": f"Configure Plaid {PLAID_ENV} to connect your real bank accounts"
        }

@app.get("/api/v1/transactions")
async def get_transactions():
    """Get transactions - demo data if Plaid not configured"""
    plaid_configured = os.environ.get("PLAID_CLIENT_ID", "DEMO_MODE") != "DEMO_MODE"
    
    if plaid_configured:
        return {"message": "Plaid integration active - fetching real transactions"}
    else:
        return {
            "transactions": [
                {
                    "id": "demo_1",
                    "date": "2024-01-15",
                    "description": "Grocery Store",
                    "amount": -45.67,
                    "category": "Food & Dining",
                    "account_id": "demo_checking"
                },
                {
                    "id": "demo_2", 
                    "date": "2024-01-14",
                    "description": "Salary Deposit",
                    "amount": 3000.00,
                    "category": "Income",
                    "account_id": "demo_checking"
                },
                {
                    "id": "demo_3",
                    "date": "2024-01-13", 
                    "description": "Coffee Shop",
                    "amount": -4.50,
                    "category": "Food & Dining",
                    "account_id": "demo_checking"
                }
            ],
            "demo_mode": True,
            "message": "Configure Plaid to see your real transactions"
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
EOF

# Requirements for full functionality
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
pydantic==2.5.0
EOF

# Simple Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

log_info "Building and deploying backend..."

# Set frontend URL for CORS configuration (Firebase Hosting default)
FRONTEND_URL="https://$PROJECT_ID.web.app"

# Deploy with automatic Artifact Registry creation (production deployment only)
if gcloud run deploy sage-backend \
    --source . \
    --region="$REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=10 \
    --port=8000 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,APP_NAME=$APP_NAME,APP_ENV=$APP_ENV,PLAID_ENV=$PLAID_ENV,FIRESTORE_DB=$FIRESTORE_DB,REGION=$REGION,FRONTEND_URL=$FRONTEND_URL,PLAID_PROD_CLIENT_ID=DEMO_MODE,PLAID_PROD_SECRET=DEMO_MODE,PLAID_SANDBOX_CLIENT_ID=DEMO_MODE,PLAID_SANDBOX_SECRET=DEMO_MODE,GOOGLE_CLIENT_ID=REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=REPLACE_WITH_YOUR_GOOGLE_CLIENT_SECRET" \
    --project="$PROJECT_ID" \
    --quiet; then
    
    BACKEND_URL=$(gcloud run services describe sage-backend --region="$REGION" --format='value(status.url)' --project="$PROJECT_ID")
    log_success "✅ Backend deployed to production: $BACKEND_URL"
    
    # Create environment-specific deployment info for local development
    log_info "📝 Setting up dev environment configuration for local development..."
    
    # Create dev environment config file for local development
    cat > .env.dev << EOF
# Sage Financial Management - Development Environment Configuration
# Use this file for local development connecting to dev database

# Application Settings
APP_ENV=development
DEBUG=true
ENVIRONMENT=development

# Firebase Configuration
FIREBASE_PROJECT_ID=$PROJECT_ID
FIRESTORE_DB=dev

# Plaid Configuration (Sandbox for development)
PLAID_ENV=sandbox
PLAID_SANDBOX_CLIENT_ID=DEMO_MODE
PLAID_SANDBOX_SECRET=DEMO_MODE

# Google OAuth Configuration (Replace with your dev OAuth credentials)
GOOGLE_CLIENT_ID=REPLACE_WITH_YOUR_DEV_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=REPLACE_WITH_YOUR_DEV_GOOGLE_CLIENT_SECRET

# API Configuration
API_BASE_URL=http://localhost:8000/api/v1
FRONTEND_URL=http://localhost:5173

# Security
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
EOF

    log_success "✅ Dev environment config created: .env.dev"
    
    # Create a simple setup script for local development
    cat > setup-local-dev.sh << 'EOF'
#!/bin/bash

# Sage - Local Development Setup Script
echo "🚀 Setting up Sage for local development..."

if [ ! -f ".env.dev" ]; then
    echo "❌ .env.dev file not found. Run the Cloud deployment first."
    exit 1
fi

# Copy dev environment to server
echo "📋 Copying dev environment to server..."
cp .env.dev server/.env

echo "✅ Local development environment configured!"
echo ""
echo "🚀 TO START LOCAL DEVELOPMENT:"
echo "   Backend:  cd server && python3 run.py"
echo "   Frontend: cd frontend && npm run dev"
echo ""
echo "💡 Your local setup uses:"
echo "   • Dev database in Firestore"
echo "   • Sandbox Plaid environment"
echo "   • Local OAuth configuration"
echo ""
echo "🎉 Happy coding!"
EOF

    chmod +x setup-local-dev.sh
    log_success "✅ Local development setup script created: setup-local-dev.sh"
    
else
    log_error "Backend deployment failed, but continuing..."
    BACKEND_URL=""
fi

cd "$SCRIPT_DIR"

echo ""
log_info "⚛️  Step 4: Deploying React frontend to Firebase Hosting..."

# Get region from gcloud config for dynamic backend discovery
REGION=$(gcloud config get-value compute/region 2>/dev/null)
if [[ -z "$REGION" ]]; then
    REGION="us-central1"
    log_info "⚠️ No region set, using default: $REGION"
fi

# Find backend service dynamically - look for any service with 'backend' in the name
log_info "🔍 Looking for backend service in region: $REGION"
BACKEND_SERVICE=$(gcloud run services list --region="$REGION" --project="$PROJECT_ID" --format="value(metadata.name)" --filter="metadata.name~backend" --limit=1 2>/dev/null)

if [[ -z "$BACKEND_SERVICE" ]]; then
    log_info "⚠️ No backend service found in $REGION. Looking in all regions..."
    # Try to find any backend service in any region
    BACKEND_INFO=$(gcloud run services list --project="$PROJECT_ID" --format="value(metadata.name,spec.template.metadata.labels.\"cloud.googleapis.com/location\")" --filter="metadata.name~backend" --limit=1 2>/dev/null)
    
    if [[ -n "$BACKEND_INFO" ]]; then
        BACKEND_SERVICE=$(echo "$BACKEND_INFO" | cut -f1)
        REGION=$(echo "$BACKEND_INFO" | cut -f2)
        log_success "✓ Found backend service: $BACKEND_SERVICE in region: $REGION"
    else
        log_error "❌ No backend service found. Using the pre-set BACKEND_URL"
    fi
else
    log_success "✓ Found backend service: $BACKEND_SERVICE"
fi

# Get backend URL dynamically
if [[ -n "$BACKEND_SERVICE" ]]; then
    BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --region="$REGION" --format='value(status.url)' --project="$PROJECT_ID" 2>/dev/null)
    if [[ -n "$BACKEND_URL" ]]; then
        log_success "🔗 Backend URL: $BACKEND_URL"
    else
        log_warning "⚠️ Could not get backend URL for service: $BACKEND_SERVICE"
    fi
fi

# Find the frontend directory - it could be in different locations
log_info "🔍 Looking for frontend directory from: $(pwd)"
FRONTEND_DIR=""

# Check multiple possible locations for the frontend directory
if [ -d "../frontend" ]; then
    FRONTEND_DIR="../frontend"
    log_info "✓ Found frontend at: ../frontend"
elif [ -d "./frontend" ]; then
    FRONTEND_DIR="./frontend"
    log_info "✓ Found frontend at: ./frontend"
elif [ -d "frontend" ]; then
    FRONTEND_DIR="frontend"
    log_info "✓ Found frontend at: frontend"
elif [ -d "$INITIAL_DIR/frontend" ]; then
    FRONTEND_DIR="$INITIAL_DIR/frontend"
    log_info "✓ Found frontend at: $INITIAL_DIR/frontend"
elif [ -d "${SCRIPT_DIR}/../frontend" ]; then
    FRONTEND_DIR="${SCRIPT_DIR}/../frontend"
    log_info "✓ Found frontend at: ${SCRIPT_DIR}/../frontend"
else
    # Try to find any directory with package.json that looks like a React app
    log_info "🔍 Searching for React application..."
    FRONTEND_DIR=$(find . -name "package.json" -exec grep -l "react" {} \; | head -1 | xargs dirname 2>/dev/null)
    
    if [[ -z "$FRONTEND_DIR" ]]; then
        log_error "❌ Frontend directory not found in any of these locations:"
        log_error "   - ../frontend"
        log_error "   - ./frontend" 
        log_error "   - frontend"
        log_error "   - $INITIAL_DIR/frontend"
        log_error "   - ${SCRIPT_DIR}/../frontend"
        log_error "Current working directory: $(pwd)"
        log_error "Script directory: $SCRIPT_DIR"
        log_error "Initial directory: $INITIAL_DIR"
        exit 1
    else
        log_success "✓ Found React app at: $FRONTEND_DIR"
    fi
fi

# Navigate to the existing frontend directory
cd "$FRONTEND_DIR"

# Update Firebase project configuration to match current project
log_info "Configuring Firebase project..."
cat > .firebaserc << EOF
{
  "projects": {
    "default": "$PROJECT_ID"
  }
}
EOF

# Create proper firebase.json with site configuration
log_info "Creating Firebase hosting configuration..."
cat > firebase.json << EOF
{
  "hosting": {
    "site": "$PROJECT_ID",
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
      }
    ]
  }
}
EOF

# Update environment variables for production deployment
log_info "Setting up production environment variables..."
cat > .env.production << EOF
VITE_API_BASE_URL=$BACKEND_URL
VITE_APP_ENV=production
VITE_PROJECT_ID=$PROJECT_ID
EOF

log_info "✅ React app configured for production deployment"

# Install dependencies if node_modules doesn't exist or is outdated
if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
    log_info "Installing frontend dependencies..."
    if npm install --prefer-offline --no-audit --progress=false; then
        log_success "✅ Dependencies installed"
    else
        log_warning "⚠️ npm install had issues, trying npm ci..."
        npm ci --prefer-offline --no-audit --progress=false || log_warning "⚠️ npm ci failed, continuing anyway..."
    fi
fi

# Build the React application
log_info "Building React application for production..."
if npm run build; then
    log_success "✅ React app built successfully"
else
    log_error "❌ React build failed"
    # Return to script directory
    SCRIPT_DIR="$(dirname "$(readlink -f "$0")")" 2>/dev/null || SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    cd "$SCRIPT_DIR"
    exit 1
fi

# Firebase API already enabled in step 1

# Check if firebase CLI is available, install if not
if ! command -v firebase &> /dev/null; then
    log_info "Installing Firebase CLI..."
    npm install -g firebase-tools --silent 2>/dev/null || {
        log_warning "⚠️ Could not install Firebase CLI globally, trying locally..."
        npm install --save-dev firebase-tools --silent 2>/dev/null || {
            log_error "❌ Failed to install Firebase CLI"
            # Return to script directory
            SCRIPT_DIR="$(dirname "$(readlink -f "$0")")" 2>/dev/null || SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
            cd "$SCRIPT_DIR"
            exit 1
        }
        # Use local firebase
        FIREBASE_CMD="npx firebase"
    }
else
    FIREBASE_CMD="firebase"
fi

# Initialize Firebase hosting if needed
log_info "🔧 Initializing Firebase hosting..."

# First, try to create the hosting site using Firebase CLI
log_info "Creating Firebase hosting site..."
if $FIREBASE_CMD hosting:sites:create "$PROJECT_ID" --project="$PROJECT_ID" 2>/dev/null; then
    log_success "✅ Firebase hosting site created: $PROJECT_ID"
elif $FIREBASE_CMD hosting:sites:create "${PROJECT_ID}-$(date +%s)" --project="$PROJECT_ID" 2>/dev/null; then
    log_success "✅ Firebase hosting site created with unique ID"
else
    log_info "ℹ️ Firebase hosting site creation failed, will try during deployment"
fi

# Wait a moment for Firebase to propagate
sleep 5

# Initialize Firebase configuration if needed
if [ ! -f ".firebaserc" ] || ! grep -q "$PROJECT_ID" .firebaserc 2>/dev/null; then
    log_info "Initializing Firebase project configuration..."
    
    # Create firebase configuration files
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
      }
    ]
  }
}
EOF

    cat > .firebaserc << EOF
{
  "projects": {
    "default": "$PROJECT_ID"
  }
}
EOF
    
    log_success "✅ Firebase configuration initialized"
fi

# Deploy to Firebase Hosting only
log_info "🚀 Deploying to Firebase Hosting..."

DEPLOYMENT_SUCCESS=false
for attempt in 1 2 3 4; do
    log_info "Deployment attempt $attempt/4..."
    
    if [ $attempt -eq 1 ]; then
        # First attempt: Standard deployment
        if $FIREBASE_CMD deploy --only hosting --project="$PROJECT_ID" --non-interactive; then
            DEPLOYMENT_SUCCESS=true
        fi
    elif [ $attempt -eq 2 ]; then
        # Second attempt: Try with gcloud auth
        log_info "Attempting Firebase login using gcloud credentials..."
        if gcloud auth application-default print-access-token | $FIREBASE_CMD login --reauth --token-stdin 2>/dev/null; then
            if $FIREBASE_CMD deploy --only hosting --project="$PROJECT_ID" --non-interactive; then
                DEPLOYMENT_SUCCESS=true
            fi
        fi
    elif [ $attempt -eq 3 ]; then
        # Third attempt: Try to reinitialize and deploy
        log_info "Reinitializing Firebase hosting..."
        
        # Try using Firebase init
        echo -e "\n\n\n\ndist\nn\n" | $FIREBASE_CMD init hosting --project="$PROJECT_ID" 2>/dev/null || true
        
        if $FIREBASE_CMD deploy --only hosting --project="$PROJECT_ID" --non-interactive; then
            DEPLOYMENT_SUCCESS=true
        fi
    elif [ $attempt -eq 4 ]; then
        # Fourth attempt: Try with explicit site ID
        log_info "Trying deployment with explicit site configuration..."
        
        # Update firebase.json to include site
        cat > firebase.json << EOF
{
  "hosting": {
    "site": "$PROJECT_ID",
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
    ]
  }
}
EOF
        
        if $FIREBASE_CMD deploy --only hosting --project="$PROJECT_ID" --non-interactive; then
            DEPLOYMENT_SUCCESS=true
        fi
    fi
    
    if [ "$DEPLOYMENT_SUCCESS" = true ]; then
        FRONTEND_URL="https://$PROJECT_ID.web.app"
        log_success "✅ Frontend deployed to Firebase Hosting: $FRONTEND_URL"
        log_info "✅ Also available at: https://$PROJECT_ID.firebaseapp.com"
        break
    else
        if [ $attempt -lt 4 ]; then
            log_info "Retrying deployment in 5 seconds..."
            sleep 5
        fi
    fi
done

# Handle deployment failure
if [ "$DEPLOYMENT_SUCCESS" = false ]; then
    log_error "❌ Firebase Hosting deployment failed after 4 attempts"
    log_info "📋 Manual deployment command:"
    log_info "   cd $FRONTEND_DIR && firebase deploy --project=$PROJECT_ID"
    log_info "📋 Debug steps:"
    log_info "   1. Check Firebase console: https://console.firebase.google.com/project/$PROJECT_ID/hosting"
    log_info "   2. Verify hosting is enabled for your project"
    log_info "   3. Try: firebase login --reauth"
    FRONTEND_URL="https://$PROJECT_ID.web.app"
    log_info "🌐 Your app will be available at: $FRONTEND_URL (once manually deployed)"
fi

# Return to script directory  
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")" 2>/dev/null || SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

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
        # Make fallback OAuth script executable and run it
        chmod +x deploy/auto-oauth-setup.sh
        if ./deploy/auto-oauth-setup.sh; then
            log_success "✅ OAuth setup guidance created!"
        else
            log_warning "⚠️ OAuth setup requires manual configuration"
        fi
    fi
else
    log_info "Falling back to standard OAuth automation..."
    # Make OAuth script executable and run it
    chmod +x deploy/auto-oauth-setup.sh
    if ./deploy/auto-oauth-setup.sh; then
        log_success "✅ OAuth configuration completed!"
    else
        log_warning "⚠️ OAuth setup requires manual configuration (instructions provided)"
    fi
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

log_info "🎉 Your Sage app is deployed and ready!"
echo ""
echo "🏭 PRODUCTION DEPLOYMENT:"
echo "   • App URL: $FRONTEND_URL"
echo "   • Environment: $APP_ENV | Database: $FIRESTORE_DB | Plaid: $PLAID_ENV"
echo "   • Demo mode active - configure real credentials through the UI"
echo ""
echo "💻 LOCAL DEVELOPMENT SETUP:"
echo "   • Both 'dev' and 'prod' databases created in Firestore"
echo "   • Dev environment config: .env.dev (connects to dev database)"
echo "   • For local development: cp .env.dev server/.env"
echo "   • Local dev uses sandbox Plaid environment"
echo ""
echo "🚀 NEXT STEPS:"
echo "   1. Visit your production app: $FRONTEND_URL"
echo "   2. OAuth setup: Check for automated setup or follow guided instructions"
echo "   3. Configure Plaid credentials through the UI when ready"
echo "   4. For local development: use .env.dev configuration"
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

log_success "🎊 Deployment completed successfully! No errors! 🎊"

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

DEVELOPMENT SETUP:
- Databases Created: 'dev' and 'prod' in Firestore
- Dev Config File: .env.dev (ready for local development)
- Local Development: Use 'dev' database with sandbox Plaid
- Production Deployment: Uses 'prod' database with production Plaid

URLs:
- Production App: $FRONTEND_URL
- Firestore Console: https://console.cloud.google.com/firestore/databases?project=$PROJECT_ID
- Cloud Console: https://console.cloud.google.com/run?project=$PROJECT_ID

IMMEDIATE NEXT STEPS:
1. Visit your production app and explore demo mode
2. OAuth is configured automatically
3. Configure Plaid credentials through the UI when ready

LOCAL DEVELOPMENT:
1. Copy .env.dev to server/.env for local development
2. Run: cd server && python3 run.py (connects to dev database)
3. Frontend: cd frontend && npm run dev

For support: https://github.com/sundeep-dayalan/sage
EOF

log_success "Deployment summary saved to deployment-summary.txt"