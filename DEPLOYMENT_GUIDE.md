# 🚀 Sage Deployment Guide

This guide explains how to deploy your own instance of Sage Financial Management App to Google Cloud.

## 📋 Prerequisites

- GitHub account
- Google Cloud Platform account with billing enabled
- 10-15 minutes of your time

## 🎯 Deployment Process

### Step 1: Fork the Repository

1. **Visit the Sage repository**: [https://github.com/sundeep-dayalan/personal-wealth-management](https://github.com/sundeep-dayalan/personal-wealth-management)
2. **Click "Fork"** in the top-right corner
3. **Select your account** as the destination
4. **Wait for the fork to complete**

### Step 2: Customize Your Fork (Optional)

Before deploying, you can customize your app:

#### Update App Branding
Edit `frontend/src/config/app.ts`:
```typescript
export const APP_CONFIG = {
  name: "Your Finance App",
  description: "Your Personal Financial Management",
  version: "1.0.0",
  // ... other settings
};
```

#### Update Colors and Styling
Edit `frontend/src/styles/globals.css` or `frontend/tailwind.config.js`

#### Add Your Features
- Modify components in `frontend/src/components/`
- Add new API endpoints in `server/app/routers/`
- Customize the dashboard layout

### Step 3: Update Deployment URL

1. **Edit your fork's README.md**
2. **Find the deployment button section**
3. **Replace `YOUR_USERNAME`** with your actual GitHub username:

```markdown
[![Deploy to Google Cloud](https://deploy.cloud.run/button.svg)](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/your-actual-username/personal-wealth-management.git&cloudshell_working_dir=.&cloudshell_tutorial=TUTORIAL.md)
```

4. **Commit the change**

### Step 4: Deploy to Google Cloud

1. **Click your updated deployment button** in your fork's README
2. **Google Cloud Shell will open** with your repository
3. **Follow the interactive tutorial** that appears
4. **Configure your app settings**:
   - App name (e.g., "My Finance App")
   - Domain (optional)
   - Plaid environment (start with "sandbox")

5. **Watch the automated deployment** (5-8 minutes):
   ```
   ✅ Enabling Google Cloud APIs
   ✅ Creating service accounts and IAM roles
   ✅ Building and deploying backend container
   ✅ Building and deploying frontend container
   ✅ Setting up Firestore database and security rules
   ✅ Configuring monitoring and budget alerts
   ```

### Step 5: Post-Deployment Configuration

After deployment completes, you'll need to set up API credentials:

#### Google OAuth Setup (2 minutes)
1. **Visit**: [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials)
2. **Create OAuth 2.0 Client ID**
3. **Add your app URLs** to authorized origins and redirect URIs
4. **Update Secret Manager** with your credentials

#### Plaid API Setup (2 minutes)
1. **Visit**: [Plaid Dashboard](https://dashboard.plaid.com/)
2. **Create account** and get API credentials
3. **Update Secret Manager** with Plaid credentials

#### Complete Setup
```bash
# Update OAuth credentials
echo "your_google_client_id" | gcloud secrets versions add sage-google-oauth-client-id --data-file=-
echo "your_google_client_secret" | gcloud secrets versions add sage-google-oauth-client-secret --data-file=-

# Update Plaid credentials  
echo "your_plaid_client_id" | gcloud secrets versions add sage-plaid-client-id --data-file=-
echo "your_plaid_secret" | gcloud secrets versions add sage-plaid-secret --data-file=-
```

### Step 6: Test Your Deployment

1. **Visit your app URL** (provided after deployment)
2. **Sign in with Google**
3. **Connect a test bank account** (Plaid sandbox)
4. **Verify data loads correctly**

## 🔧 Ongoing Management

### Keeping Your Fork Updated

To get new features from the main repository:

```bash
# Add the main repo as upstream
git remote add upstream https://github.com/sundeep-dayalan/personal-wealth-management.git

# Fetch and merge updates
git fetch upstream
git checkout main
git merge upstream/main

# Push updates to your fork
git push origin main
```

### Redeploying After Updates

After updating your fork:
1. **Visit Google Cloud Run console**
2. **Click your service** (sage-backend or sage-frontend)
3. **Click "Deploy new revision"**
4. **Select "Deploy from source"**
5. **Connect to your GitHub fork**

Or use the command line:
```bash
cd personal-wealth-management
gcloud run deploy sage-backend --source ./server --region us-central1
gcloud run deploy sage-frontend --source ./frontend --region us-central1
```

### Monitoring and Costs

- **Monitor costs**: Check Google Cloud billing dashboard
- **Budget alerts**: Automatically set to $10/month
- **View logs**: Use Cloud Logging for debugging
- **Health checks**: Built-in monitoring for uptime

## 🎯 Benefits of This Approach

### For Users
- **Full Control**: Your data, your infrastructure, your customizations
- **Cost Transparency**: Clear pricing, budget alerts, no hidden fees
- **Customizable**: Modify before deploying, add your own features
- **Updatable**: Easy to pull new features from main repo

### For the Open Source Project
- **Scalable**: No central infrastructure costs
- **Secure**: No access to user data or credentials
- **Flexible**: Users can modify and extend as needed
- **Community**: Users can contribute improvements back

## 🆘 Troubleshooting

### Common Issues

**Deployment Button Not Working**
- Ensure your repository is public or you're signed into GitHub
- Check that you updated the GitHub username in the URL

**API Credentials Issues**
- Verify OAuth redirect URIs match your exact app URL
- Check Plaid environment matches your account type
- Ensure secrets are properly formatted in Secret Manager

**Application Not Loading**
- Check Cloud Run logs for errors
- Verify environment variables are set correctly
- Test health endpoints for backend and frontend

### Getting Help

1. **Check deployment logs** in Google Cloud Console
2. **Review the troubleshooting guide** in `deploy/env-setup-guide.md`
3. **Open an issue** in the main repository
4. **Join the community** for support and feature requests

## 🎉 You're Live!

Once deployed, you'll have:
- ✅ Your own financial management app
- ✅ Secure bank account connections via Plaid
- ✅ Google OAuth authentication
- ✅ Production-ready infrastructure on Google Cloud
- ✅ Full control over your data and deployment
- ✅ Ability to customize and extend features

Welcome to taking control of your financial data! 💰