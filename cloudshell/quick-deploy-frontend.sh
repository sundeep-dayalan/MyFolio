#!/bin/bash

# Quick Frontend Deployment - No Prompts
# This creates the site and deploys in one go

set -e

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ No project selected. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "🚀 Quick Frontend Deployment for: $PROJECT_ID"

# Navigate to frontend
cd ~/cloudshell_open/sage/frontend

# Create unique site ID
SITE_ID="${PROJECT_ID}-frontend-$(date +%s)"

echo "🔧 Creating Firebase hosting site: $SITE_ID"

# Method 1: Try REST API
if gcloud auth application-default print-access-token > /tmp/token.txt 2>/dev/null; then
    ACCESS_TOKEN=$(cat /tmp/token.txt)
    
    HTTP_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/response.json \
        -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"siteId\": \"$SITE_ID\"}" \
        "https://firebasehosting.googleapis.com/v1beta1/projects/$PROJECT_ID/sites" 2>/dev/null || echo "000")
    
    if [[ "$HTTP_RESPONSE" == "200" ]] || [[ "$HTTP_RESPONSE" == "201" ]]; then
        echo "✅ Site created via API"
        SITE_CREATED=true
    else
        echo "ℹ️ API failed, trying CLI..."
        SITE_CREATED=false
    fi
    
    rm -f /tmp/token.txt /tmp/response.json
else
    SITE_CREATED=false
fi

# Method 2: Firebase CLI with timeout
if [[ "$SITE_CREATED" != "true" ]]; then
    echo "🔧 Creating site via Firebase CLI..."
    echo "$SITE_ID" | timeout 30 firebase hosting:sites:create --project="$PROJECT_ID" && {
        echo "✅ Site created via CLI"
        SITE_CREATED=true
    } || {
        echo "ℹ️ Using default project site"
        SITE_ID="$PROJECT_ID"
    }
fi

# Create Firebase configuration
echo "📝 Creating Firebase configuration..."
cat > firebase.json << EOF
{
  "hosting": {
    "site": "$SITE_ID",
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

cat > .firebaserc << EOF
{
  "projects": {
    "default": "$PROJECT_ID"
  }
}
EOF

# Deploy
echo "🚀 Deploying to Firebase Hosting..."
if firebase deploy --only hosting --project="$PROJECT_ID" --non-interactive; then
    echo ""
    echo "🎉 SUCCESS! Frontend deployed!"
    echo "🌐 Your app is live at: https://$SITE_ID.web.app"
    echo ""
else
    echo "❌ Deployment failed"
    exit 1
fi