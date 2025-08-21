# 🚀 Deploy Sage Financial Management App to Google Cloud

Welcome! This tutorial will deploy your personal financial management application to Google Cloud in just a few minutes.

## 📋 Prerequisites Check

✅ You're logged into Google Cloud Console  
✅ You have a Google Cloud Project selected  
✅ Billing is enabled on your project  

Current project: **`{{PROJECT_ID}}`**  
Current user: **`{{USER_EMAIL}}`**

---

## 🎯 What We'll Deploy

- **Backend API**: FastAPI server on Cloud Run
- **Frontend App**: React application on Cloud Run  
- **Database**: Firestore for user data and transactions
- **Authentication**: Google OAuth integration
- **Monitoring**: Basic logging and error tracking

**Estimated time**: 5-10 minutes ⏱️

---

## Step 1: Project Configuration

Let's confirm your project settings:

```bash
echo "Current project: $(gcloud config get-value project)"
echo "Current region: $(gcloud config get-value compute/region)"
```

<walkthrough-editor-open-file filePath="cloudshell/setup.sh">Click here to open the setup script</walkthrough-editor-open-file>

**Would you like to continue with this project?** If yes, proceed to Step 2.

---

## Step 2: Application Configuration

Please provide the following details for your application:

### App Information
- **App Name**: (e.g., "My Finance App")
- **Domain** (optional): (e.g., "myfinanceapp.com" - leave blank for auto-generated URL)

### Plaid Configuration (for bank connections)
- **Environment**: `sandbox` (recommended for testing) or `production`

> **Note**: You'll need to set up your Plaid credentials after deployment. We'll provide instructions at the end.

---

## Step 3: Deploy! 🚀

Ready to deploy? Run the setup script:

```bash
chmod +x cloudshell/setup.sh
./cloudshell/setup.sh
```

The setup script will automatically use our bulletproof deployment system for a smooth, reliable experience!

<walkthrough-editor-open-file filePath="deploy/deploy.sh">You can also view the deployment script</walkthrough-editor-open-file>

This will:
1. ✅ Enable required Google Cloud APIs
2. ✅ Create service accounts with proper permissions  
3. ✅ Build and deploy backend to Cloud Run
4. ✅ Build and deploy frontend to Cloud Run
5. ✅ Set up Firestore database
6. ✅ Configure Google OAuth
7. ✅ Set up monitoring and budget alerts

---

## Step 4: Post-Deployment Setup

After deployment completes, you'll need to:

### 1. Configure Plaid Credentials
1. Go to [Plaid Dashboard](https://dashboard.plaid.com/)
2. Create an account/sign in
3. Get your `CLIENT_ID` and `SECRET`
4. Update your Cloud Run service environment variables

### 2. Set up Google OAuth
1. Go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
2. Find your OAuth 2.0 client
3. Add your app domain to authorized origins

### 3. Test Your Application
- Visit your app URL (provided after deployment)
- Try logging in with Google
- Connect a test bank account (sandbox mode)

---

## 🎉 Deployment Complete!

Once the script finishes, you'll see:

```
🎉 Deployment Complete!

📱 Your App: https://sage-frontend-[PROJECT-ID].a.run.app
🔐 Backend API: https://sage-backend-[PROJECT-ID].a.run.app
📊 Firestore: https://console.cloud.google.com/firestore

🔑 Login with your Google account
💰 Budget Alert: Set at $10/month
📈 Monitoring: Enabled with Cloud Logging

📧 Setup details available in Cloud Console
```

---

## 🔧 Next Steps

1. **Customize your app**: Edit the code and redeploy
2. **Set up CI/CD**: Use the included GitHub Actions workflow  
3. **Add custom domain**: Configure DNS in Cloud Console
4. **Scale resources**: Adjust Cloud Run settings as needed

---

## 🆘 Need Help?

- **Logs**: Check Cloud Run logs in Google Cloud Console
- **Issues**: Visit the project repository issues page
- **Documentation**: See the full docs in the repository

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

**Congratulations!** Your financial management app is now running on Google Cloud! 🎊