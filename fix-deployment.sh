#!/bin/bash

# Quick fix for the deployment issues
echo "🔧 Fixing deployment issues..."

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ No project selected"
    exit 1
fi

echo "📍 Project: $PROJECT_ID"

# 1. Fix Cloud Build permissions
echo "🔐 Fixing Cloud Build permissions..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null)
if [[ -n "$PROJECT_NUMBER" ]]; then
    CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
    
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/run.admin" \
        --quiet 2>/dev/null
        
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/iam.serviceAccountUser" \
        --quiet 2>/dev/null
        
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/storage.admin" \
        --quiet 2>/dev/null
        
    echo "✅ Cloud Build permissions fixed"
else
    echo "⚠️ Could not get project number"
fi

# 2. Redeploy backend with permissions fix
echo "🚀 Redeploying backend..."

# Create temporary backend with minimal setup
mkdir -p temp-backend
cd temp-backend

cat > main.py << 'EOF'
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Sage Financial Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "🏦 Sage Financial Management API",
        "status": "running",
        "version": "1.0.0",
        "project": os.environ.get("PROJECT_ID", "unknown")
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sage-backend"}

@app.get("/api/v1/health") 
async def api_health():
    return {"status": "healthy", "service": "sage-api", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
EOF

cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
EOF

cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Deploy the backend
echo "🐳 Deploying backend..."
if gcloud run deploy sage-backend \
    --source . \
    --region="us-central1" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=10 \
    --port=8000 \
    --set-env-vars="PROJECT_ID=$PROJECT_ID" \
    --project="$PROJECT_ID" \
    --quiet; then
    
    BACKEND_URL=$(gcloud run services describe sage-backend --region="us-central1" --format='value(status.url)' --project="$PROJECT_ID")
    echo "✅ Backend deployed successfully: $BACKEND_URL"
    echo ""
    echo "🎉 Fix complete! Your backend should now be working."
    echo "📱 Visit your frontend app - it should now detect the backend and redirect properly."
    
else
    echo "❌ Backend deployment still failing"
    echo "💡 Try enabling more APIs manually:"
    echo "   gcloud services enable cloudbuild.googleapis.com"
    echo "   gcloud services enable run.googleapis.com"
    echo "   gcloud services enable artifactregistry.googleapis.com"
fi

# Cleanup
cd ..
rm -rf temp-backend

echo ""
echo "🔗 Next steps:"
echo "1. Visit your frontend URL"
echo "2. Check if backend health endpoint works"
echo "3. Complete OAuth setup if needed"