#!/bin/bash

# Quick Frontend Deployment Fix
# This script enables the Firebase Hosting API and deploys the frontend

set -e

# Get project ID from gcloud config
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ No project selected. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Get region from gcloud config
REGION=$(gcloud config get-value compute/region 2>/dev/null)
if [[ -z "$REGION" ]]; then
    REGION="us-central1"
    echo "⚠️ No region set, using default: $REGION"
fi

# Find backend service - look for any service with 'backend' in the name
echo "🔍 Looking for backend service in region: $REGION"
BACKEND_SERVICE=$(gcloud run services list --region="$REGION" --project="$PROJECT_ID" --format="value(metadata.name)" --filter="metadata.name~backend" --limit=1 2>/dev/null)

if [[ -z "$BACKEND_SERVICE" ]]; then
    echo "⚠️ No backend service found. Looking in all regions..."
    # Try to find any backend service in any region
    BACKEND_INFO=$(gcloud run services list --project="$PROJECT_ID" --format="value(metadata.name,spec.template.metadata.labels.\"cloud.googleapis.com/location\")" --filter="metadata.name~backend" --limit=1 2>/dev/null)
    
    if [[ -n "$BACKEND_INFO" ]]; then
        BACKEND_SERVICE=$(echo "$BACKEND_INFO" | cut -f1)
        REGION=$(echo "$BACKEND_INFO" | cut -f2)
        echo "✓ Found backend service: $BACKEND_SERVICE in region: $REGION"
    else
        echo "❌ No backend service found. Please deploy backend first."
        exit 1
    fi
else
    echo "✓ Found backend service: $BACKEND_SERVICE"
fi

# Get backend URL
BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --region="$REGION" --format='value(status.url)' --project="$PROJECT_ID" 2>/dev/null)

if [[ -z "$BACKEND_URL" ]]; then
    echo "❌ Could not get backend URL for service: $BACKEND_SERVICE"
    exit 1
fi

echo "🔗 Backend URL: $BACKEND_URL"

echo "🚀 Deploying frontend for project: $PROJECT_ID"

# Enable Firebase Hosting API first
echo "🔧 Enabling Firebase Hosting API..."
gcloud services enable firebasehosting.googleapis.com --project="$PROJECT_ID"

# Wait for API to be fully enabled
echo "⏳ Waiting for API to be fully enabled..."
sleep 15

# Find frontend directory dynamically
echo "📂 Looking for frontend directory..."
FRONTEND_DIR=""

# Check multiple possible locations
if [ -d "./frontend" ]; then
    FRONTEND_DIR="./frontend"
elif [ -d "../frontend" ]; then
    FRONTEND_DIR="../frontend"
elif [ -d "frontend" ]; then
    FRONTEND_DIR="frontend"
elif [ -d "~/cloudshell_open/sage/frontend" ]; then
    FRONTEND_DIR="~/cloudshell_open/sage/frontend"
else
    # Try to find any directory with package.json that looks like a React app
    echo "🔍 Searching for React application..."
    FRONTEND_DIR=$(find . -name "package.json" -exec grep -l "react" {} \; | head -1 | xargs dirname 2>/dev/null)
    
    if [[ -z "$FRONTEND_DIR" ]]; then
        echo "❌ Could not find frontend directory with React application"
        echo "Please ensure you're running this from a directory that contains a 'frontend' folder"
        exit 1
    fi
fi

echo "✓ Found frontend directory: $FRONTEND_DIR"
cd "$FRONTEND_DIR"

# Update environment variables
echo "📝 Setting up production environment..."
cat > .env.production << EOF
VITE_API_BASE_URL=$BACKEND_URL
VITE_APP_ENV=production
VITE_PROJECT_ID=$PROJECT_ID
EOF

# Create proper Firebase configuration
echo "🔧 Creating Firebase configuration..."
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

cat > .firebaserc << EOF
{
  "projects": {
    "default": "$PROJECT_ID"
  }
}
EOF

# Build if needed
if [ ! -d "dist" ] || [ ! "$(ls -A dist 2>/dev/null)" ]; then
    echo "📦 Building React application..."
    npm run build
fi

# Deploy to Firebase Hosting
echo "🚀 Deploying to Firebase Hosting..."
if firebase deploy --only hosting --project="$PROJECT_ID" --non-interactive; then
    echo ""
    echo "🎉 SUCCESS! Frontend deployed successfully!"
    echo "🌐 Your app is now available at:"
    echo "   - https://$PROJECT_ID.web.app"
    echo "   - https://$PROJECT_ID.firebaseapp.com"
    echo ""
    echo "🔗 Backend API: $BACKEND_URL"
    echo ""
else
    echo "❌ Firebase deployment failed. Trying App Engine as fallback..."
    
    # Create App Engine configuration
    cat > app.yaml << EOF
runtime: nodejs18
service: default

handlers:
- url: /(.*\\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|map))$
  static_files: dist/\\1
  upload: dist/(.*\\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|map))$
  secure: always

- url: /.*
  static_files: dist/index.html
  upload: dist/index.html
  secure: always

automatic_scaling:
  min_instances: 0
  max_instances: 10
EOF
    
    # Deploy to App Engine
    if gcloud app deploy app.yaml --project="$PROJECT_ID" --quiet; then
        echo ""
        echo "🎉 SUCCESS! Frontend deployed to App Engine!"
        echo "🌐 Your app is now available at: https://$PROJECT_ID.appspot.com"
        echo ""
        echo "🔗 Backend API: $BACKEND_URL"
        echo ""
    else
        echo "❌ Both Firebase and App Engine deployments failed."
        echo "Please check the error messages above and try again."
        exit 1
    fi
fi