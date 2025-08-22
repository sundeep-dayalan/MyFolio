#!/bin/bash

# Test build script to verify deployments work locally
set -e

echo "🚀 Testing Frontend Build..."
cd frontend

echo "📦 Installing dependencies..."
npm install

echo "🔨 Building frontend..."
VITE_API_BASE_URL=https://sage-24293-api.azurewebsites.net/api npm run build

if [ -d "dist" ]; then
    echo "✅ Frontend build successful!"
    echo "📊 Build size:"
    du -sh dist
    echo "📁 Build contents:"
    ls -la dist
else
    echo "❌ Frontend build failed!"
    exit 1
fi

cd ..

echo "🚀 Testing Backend Package..."
cd server-azure

echo "🐍 Setting up Python environment..."
python3 -m venv .test-venv
source .test-venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📦 Creating deployment package..."
zip -r test-deployment.zip . -x ".test-venv/*" "__pycache__/*" "*.pyc" ".git/*" "tests/*"

if [ -f "test-deployment.zip" ]; then
    echo "✅ Backend package created successfully!"
    echo "📊 Package size:"
    ls -lh test-deployment.zip
    rm test-deployment.zip
else
    echo "❌ Backend packaging failed!"
    deactivate
    exit 1
fi

deactivate
rm -rf .test-venv

cd ..

echo "🎉 All tests passed! Deployments should work."