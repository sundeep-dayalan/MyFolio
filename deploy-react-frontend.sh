#!/bin/bash

# Deploy the actual React frontend instead of dummy page
echo "🚀 Deploying actual React frontend..."

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ No project selected"
    exit 1
fi

# Get the backend URL for environment configuration
BACKEND_URL=$(gcloud run services describe sage-backend --region="us-central1" --format='value(status.url)' --project="$PROJECT_ID" 2>/dev/null)

echo "📍 Project: $PROJECT_ID"
echo "🔗 Backend: $BACKEND_URL"

# Copy frontend directory for deployment
echo "📋 Preparing React app for deployment..."
rm -rf temp-frontend
cp -r frontend temp-frontend
cd temp-frontend

# Create production environment configuration
echo "⚙️ Configuring production environment..."
cat > .env.production << EOF
VITE_API_BASE_URL=$BACKEND_URL
VITE_APP_ENV=production
VITE_PROJECT_ID=$PROJECT_ID
EOF

echo "✅ Environment configured"

# Deploy the React application using its existing Dockerfile
echo "🐳 Deploying React app to Cloud Run..."

if gcloud run deploy sage-frontend \
    --source . \
    --region="us-central1" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --max-instances=5 \
    --port=8080 \
    --project="$PROJECT_ID" \
    --quiet; then
    
    FRONTEND_URL=$(gcloud run services describe sage-frontend --region="us-central1" --format='value(status.url)' --project="$PROJECT_ID")
    echo ""
    echo "✅ React frontend deployed successfully!"
    echo "🌐 Frontend URL: $FRONTEND_URL"
    echo ""
    echo "🎉 Your actual React financial management app is now live!"
    echo "📱 Visit: $FRONTEND_URL"
    echo ""
    echo "Features available:"
    echo "  • 📊 Dashboard with financial overview"
    echo "  • 🏦 Account management"
    echo "  • 💳 Transaction history"
    echo "  • 🔐 Google OAuth integration"
    echo "  • 🔗 Plaid bank connections"
    echo ""
else
    echo "❌ Frontend deployment failed"
    echo "💡 Check the logs for more details:"
    echo "   gcloud logs read --service=sage-frontend --limit=50"
fi

# Cleanup
cd ..
rm -rf temp-frontend

echo "🎊 Deployment complete!"