#!/bin/bash

# Fix Frontend Deployment to Firebase Hosting
# This script fixes the Firebase hosting deployment issue

set -e

PROJECT_ID="sage-auto-setup2"
BACKEND_URL="https://sage-backend-5rugdscsaq-uc.a.run.app"

echo "🚀 Fixing Firebase Hosting deployment for project: $PROJECT_ID"

# Navigate to frontend directory
cd ../frontend

# Update environment variables
echo "📝 Setting up production environment..."
cat > .env.production << EOF
VITE_API_BASE_URL=$BACKEND_URL
VITE_APP_ENV=production
VITE_PROJECT_ID=$PROJECT_ID
EOF

# Initialize Firebase hosting if not already done
echo "🔧 Initializing Firebase hosting..."

# Create proper firebase.json with site configuration
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

# Update .firebaserc
cat > .firebaserc << EOF
{
  "projects": {
    "default": "$PROJECT_ID"
  }
}
EOF

echo "✅ Firebase configuration updated"

# Check if dist directory exists, if not build
if [ ! -d "dist" ]; then
    echo "📦 Building React application..."
    npm run build
fi

echo "🚀 Deploying to Firebase Hosting..."

# Try multiple deployment methods
if command -v firebase &> /dev/null; then
    echo "Using Firebase CLI..."
    firebase deploy --only hosting --project="$PROJECT_ID" --non-interactive
elif command -v gcloud &> /dev/null; then
    echo "Creating App Engine fallback deployment..."
    
    # Create app.yaml for App Engine
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
    gcloud app deploy app.yaml --project="$PROJECT_ID" --quiet
    
    echo "✅ Deployed to App Engine: https://$PROJECT_ID.appspot.com"
else
    echo "❌ Neither Firebase CLI nor gcloud available"
    echo "📋 Manual steps needed:"
    echo "1. Install Firebase CLI: npm install -g firebase-tools"
    echo "2. Run: firebase deploy --project=$PROJECT_ID"
    exit 1
fi

echo ""
echo "🎉 Frontend deployment completed!"
echo "🌐 Your app should be available at:"
echo "   - https://$PROJECT_ID.web.app"
echo "   - https://$PROJECT_ID.firebaseapp.com"
echo "   - https://$PROJECT_ID.appspot.com (if App Engine was used)"
echo ""