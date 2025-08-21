#!/bin/bash

# Deploy React App to Cloud Storage + CDN (Free Tier)
# This bypasses App Engine issues and provides better performance

set -e

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ No project selected. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "🚀 Deploying React app to Cloud Storage for project: $PROJECT_ID"

# Navigate to frontend
cd ~/cloudshell_open/sage/frontend

# Create unique bucket name
BUCKET_NAME="${PROJECT_ID}-frontend-$(date +%s)"

echo "🪣 Creating Cloud Storage bucket: $BUCKET_NAME"

# Create bucket for static website hosting
if gsutil mb -p "$PROJECT_ID" "gs://$BUCKET_NAME"; then
    echo "✅ Bucket created: $BUCKET_NAME"
else
    echo "❌ Failed to create bucket"
    exit 1
fi

# Configure bucket for public website hosting
echo "🌐 Configuring bucket for website hosting..."
gsutil web set -m index.html -e index.html "gs://$BUCKET_NAME"

# Make all objects publicly readable
gsutil iam ch allUsers:objectViewer "gs://$BUCKET_NAME"

# Upload all files from dist directory
echo "📤 Uploading React app files..."
gsutil -m cp -r dist/* "gs://$BUCKET_NAME/"

# Set proper content types
gsutil -m setmeta -h "Content-Type:text/html" "gs://$BUCKET_NAME/index.html"
gsutil -m setmeta -h "Content-Type:text/css" "gs://$BUCKET_NAME/*.css"
gsutil -m setmeta -h "Content-Type:application/javascript" "gs://$BUCKET_NAME/*.js"

# Set cache control
gsutil -m setmeta -h "Cache-Control:public, max-age=86400" "gs://$BUCKET_NAME/*"

# Get the public URL
PUBLIC_URL="https://storage.googleapis.com/$BUCKET_NAME/index.html"

echo ""
echo "🎉 SUCCESS! React app deployed to Cloud Storage!"
echo "🌐 Your app is live at: $PUBLIC_URL"
echo "🪣 Bucket name: $BUCKET_NAME"
echo ""
echo "💡 This deployment is completely free and has no instance limits!"
echo ""

# Save the URL for reference
echo "$PUBLIC_URL" > ../deployment-url.txt
echo "📝 URL saved to: ../deployment-url.txt"