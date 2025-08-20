#!/bin/bash

# Main deployment script for Sage Financial Management App
# Handles building and deploying both backend and frontend to Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[DEPLOY]${NC} $1"
}

log_error() {
    echo -e "${RED}[DEPLOY]${NC} $1"
}

# Check required environment variables
if [[ -z "$PROJECT_ID" ]]; then
    log_error "PROJECT_ID environment variable not set"
    exit 1
fi

if [[ -z "$REGION" ]]; then
    REGION="us-central1"
    log_info "Using default region: $REGION"
fi

# Generate unique service names
BACKEND_SERVICE="sage-backend"
FRONTEND_SERVICE="sage-frontend"

log_info "Starting application deployment..."
log_info "Project: $PROJECT_ID"
log_info "Region: $REGION"
log_info "Backend service: $BACKEND_SERVICE"
log_info "Frontend service: $FRONTEND_SERVICE"

# Create deployment directory for build artifacts
mkdir -p .deploy

# ============================================================================
# BACKEND DEPLOYMENT
# ============================================================================

log_info "🐍 Building and deploying backend (FastAPI)..."

# Create production requirements.txt if it doesn't exist
if [[ ! -f "server/requirements-prod.txt" ]]; then
    log_info "Creating production requirements file..."
    cat > server/requirements-prod.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
firebase-admin==6.2.0
plaid-python==12.0.0
cryptography==41.0.7
python-dotenv==1.0.0
google-cloud-firestore==2.13.1
google-auth==2.23.4
requests==2.31.0
EOF
fi

# Create Dockerfile for backend if it doesn't exist
if [[ ! -f "server/Dockerfile" ]]; then
    log_info "Creating backend Dockerfile..."
    cat > server/Dockerfile << 'EOF'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
fi

# Create .dockerignore for backend
cat > server/.dockerignore << 'EOF'
__pycache__
*.pyc
*.pyo
*.pyd
.Python
.git
.gitignore
README.md
Dockerfile
.dockerignore
.env
.env.*
tests/
.pytest_cache/
.coverage
htmlcov/
*.log
EOF

# Build and deploy backend
log_info "Building backend container..."
cd server

# Create a simple health check endpoint if it doesn't exist
if [[ ! -f "app/health.py" ]]; then
    mkdir -p app
    cat > app/health.py << 'EOF'
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sage-backend"}
EOF
fi

# Deploy to Cloud Run
gcloud run deploy $BACKEND_SERVICE \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars="PROJECT_ID=$PROJECT_ID,PLAID_ENV=${PLAID_ENV:-sandbox}" \
    --memory=1Gi \
    --cpu=1 \
    --concurrency=100 \
    --max-instances=10 \
    --timeout=300 \
    --port=8000

if [[ $? -eq 0 ]]; then
    log_success "Backend deployed successfully!"
    BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region=$REGION --format='value(status.url)')
    log_success "Backend URL: $BACKEND_URL"
else
    log_error "Backend deployment failed!"
    exit 1
fi

cd ..

# ============================================================================
# FRONTEND DEPLOYMENT
# ============================================================================

log_info "⚛️  Building and deploying frontend (React)..."

# Create production environment file
log_info "Creating production environment configuration..."
cat > frontend/.env.production << EOF
VITE_API_BASE_URL=$BACKEND_URL/api/v1
VITE_APP_ENV=production
VITE_APP_NAME=${APP_NAME:-Sage Finance}
VITE_PLAID_ENV=${PLAID_ENV:-sandbox}
EOF

# Create Dockerfile for frontend if it doesn't exist
if [[ ! -f "frontend/Dockerfile" ]]; then
    log_info "Creating frontend Dockerfile..."
    cat > frontend/Dockerfile << 'EOF'
# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 8080 (Cloud Run requirement)
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
EOF
fi

# Create nginx configuration for frontend
cat > frontend/nginx.conf << 'EOF'
server {
    listen 8080;
    server_name localhost;
    
    root /usr/share/nginx/html;
    index index.html index.htm;
    
    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Handle client-side routing
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Create .dockerignore for frontend
cat > frontend/.dockerignore << 'EOF'
node_modules
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.git
.gitignore
README.md
Dockerfile
.dockerignore
.env.local
.env.development
.env.test
.DS_Store
dist/
build/
coverage/
.nyc_output
EOF

# Build and deploy frontend
log_info "Building frontend container..."
cd frontend

# Install dependencies if needed
if [[ ! -d "node_modules" ]]; then
    log_info "Installing frontend dependencies..."
    npm install
fi

# Deploy to Cloud Run
gcloud run deploy $FRONTEND_SERVICE \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --concurrency=100 \
    --max-instances=5 \
    --timeout=300 \
    --port=8080

if [[ $? -eq 0 ]]; then
    log_success "Frontend deployed successfully!"
    FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region=$REGION --format='value(status.url)')
    log_success "Frontend URL: $FRONTEND_URL"
else
    log_error "Frontend deployment failed!"
    exit 1
fi

cd ..

# ============================================================================
# POST-DEPLOYMENT CONFIGURATION
# ============================================================================

log_info "🔧 Configuring post-deployment settings..."

# Update backend with frontend URL for CORS
log_info "Updating backend CORS configuration..."
gcloud run services update $BACKEND_SERVICE \
    --region=$REGION \
    --update-env-vars="FRONTEND_URL=$FRONTEND_URL"

# Store URLs in environment for other scripts
export BACKEND_URL
export FRONTEND_URL

log_success "Application deployment completed!"
log_success "Backend: $BACKEND_URL"
log_success "Frontend: $FRONTEND_URL"

# Create deployment summary
cat > .deploy/deployment-summary.json << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "project_id": "$PROJECT_ID",
  "region": "$REGION",
  "app_name": "${APP_NAME:-Sage Finance}",
  "plaid_env": "${PLAID_ENV:-sandbox}",
  "services": {
    "backend": {
      "name": "$BACKEND_SERVICE",
      "url": "$BACKEND_URL"
    },
    "frontend": {
      "name": "$FRONTEND_SERVICE",
      "url": "$FRONTEND_URL"
    }
  }
}
EOF

log_success "Deployment summary saved to .deploy/deployment-summary.json"