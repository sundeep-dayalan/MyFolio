# GitHub Actions CI/CD Setup Guide

## 🚀 Automatic Deployment Setup

This guide will configure automatic deployments for both your frontend and backend when you push code to GitHub.

## 📋 Required GitHub Secrets

You need to add these secrets to your GitHub repository for automatic deployments to work:

### 1. Backend Function App Secret

**Secret Name:** `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`

**How to get it:**
```bash
# Download the publish profile for your Function App
az functionapp deployment list-publishing-profiles \
  --name sage-24293-api \
  --resource-group sage-financial-app-rg-22958 \
  --xml
```

Copy the entire XML output and add it as a secret.

### 2. Frontend Static Web App Secret

**Secret Name:** `AZURE_STATIC_WEB_APPS_API_TOKEN`

**How to get it:**
```bash
# Get the Static Web App deployment token
az staticwebapp secrets list \
  --name sage-25008-web \
  --resource-group sage-financial-app-rg-22958 \
  --query "properties.apiKey" \
  --output tsv
```

Copy the token and add it as a secret.

## 🔧 Adding Secrets to GitHub

1. **Go to your GitHub repository**
2. **Click Settings tab**
3. **Go to Secrets and variables → Actions**
4. **Click "New repository secret"**
5. **Add each secret with the exact names above**

## 📦 How It Works

### Backend Deployment (Azure Functions)
- **Triggers:** When you push changes to `server-azure/` folder
- **Process:** 
  1. Sets up Python 3.11 environment
  2. Installs dependencies
  3. Creates deployment zip
  4. Deploys to Azure Functions
  5. Tests health endpoint

### Frontend Deployment (Static Web Apps)
- **Triggers:** When you push changes to `frontend/` folder  
- **Process:**
  1. Sets up Node.js 18 environment
  2. Installs npm dependencies
  3. Builds React app with production config
  4. Deploys to Azure Static Web Apps

## 🎯 Current Configuration

Your workflows are configured for:

- **Function App:** `sage-24293-api`
- **Static Web App:** `sage-25008-web`
- **Resource Group:** `sage-financial-app-rg-22958`
- **Backend URL:** `https://sage-24293-api.azurewebsites.net`
- **Frontend URL:** `https://red-bush-038dd4710.1.azurestaticapps.net`

## 🚀 Testing Automatic Deployment

After setting up the secrets:

1. **Make a change to your backend:**
   ```bash
   # Edit a file in server-azure/
   echo "# Updated" >> server-azure/README.md
   git add server-azure/
   git commit -m "test: backend deployment"
   git push
   ```

2. **Make a change to your frontend:**
   ```bash
   # Edit a file in frontend/
   echo "# Updated" >> frontend/README.md
   git add frontend/
   git commit -m "test: frontend deployment"
   git push
   ```

3. **Check GitHub Actions:**
   - Go to your repository → Actions tab
   - You should see workflows running automatically

## 🔍 Monitoring Deployments

- **GitHub Actions:** Monitor build and deployment logs
- **Azure Portal:** Check Function App and Static Web App status
- **Application Insights:** Monitor performance and errors

## ⚡ Deployment Triggers

- **Manual:** You can trigger deployments manually from GitHub Actions
- **Pull Requests:** Deployments also run on PRs for testing
- **Main Branch:** Automatic deployments on pushes to main branch

## 🛠️ Customization

To modify the deployment configuration, edit:
- `.github/workflows/azure-functions.yml` - Backend deployment
- `.github/workflows/azure-static-web-apps.yml` - Frontend deployment

## 🆘 Troubleshooting

### Common Issues:

1. **"Secret not found"**
   - Verify secret names match exactly (case-sensitive)
   - Check secrets are added to repository settings

2. **"Deployment failed"**
   - Check Azure resources are still running
   - Verify publish profiles haven't expired

3. **"Health check failed"**
   - Function App may need 1-2 minutes to start
   - Check Application Insights for error logs

### Getting Help:

- Check GitHub Actions logs for detailed error messages
- Use Azure Portal to monitor resource health
- Review Application Insights for runtime issues

---

## 🎉 Once Setup Complete

After configuring the secrets, your repository will have:

✅ **Automatic Backend Deployment** when server-azure/ changes
✅ **Automatic Frontend Deployment** when frontend/ changes  
✅ **Pull Request Testing** for both components
✅ **Manual Deployment Triggers** available anytime

**Your Sage Financial Management App will auto-deploy on every push to main!**