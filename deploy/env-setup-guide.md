# Environment Setup Guide

This guide will help you configure the necessary environment variables and API credentials for your Sage Financial Management application after deployment.

## 📋 Post-Deployment Checklist

After running the one-click deployment, you'll need to complete these configuration steps:

### 1. 🔐 Google OAuth Setup

#### Create OAuth Credentials

1. Visit [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Select "Web application"
4. Configure the following:

**Authorized JavaScript Origins:**
```
https://your-frontend-url.a.run.app
http://localhost:5173
http://localhost:3000
```

**Authorized Redirect URIs:**
```
https://your-frontend-url.a.run.app/auth/callback
https://your-frontend-url.a.run.app/login/callback
http://localhost:5173/auth/callback
http://localhost:3000/auth/callback
```

#### Update Secret Manager

Replace the placeholder values in Google Secret Manager:

```bash
# Update OAuth Client ID
echo "YOUR_ACTUAL_CLIENT_ID" | gcloud secrets versions add sage-google-oauth-client-id --data-file=-

# Update OAuth Client Secret
echo "YOUR_ACTUAL_CLIENT_SECRET" | gcloud secrets versions add sage-google-oauth-client-secret --data-file=-
```

### 2. 🏦 Plaid API Setup

#### Create Plaid Account

1. Visit [Plaid Dashboard](https://dashboard.plaid.com/)
2. Sign up or log in to your account
3. Create a new application
4. Get your Client ID and Secret

#### Configure Plaid Environment

For **Development/Testing** (recommended first):
```bash
# Sandbox environment for testing
echo "your-plaid-client-id" | gcloud secrets versions add sage-plaid-client-id --data-file=-
echo "your-plaid-sandbox-secret" | gcloud secrets versions add sage-plaid-secret --data-file=-
```

For **Production** (when ready for real bank data):
```bash
# Production environment for live data
echo "your-plaid-client-id" | gcloud secrets versions add sage-plaid-client-id --data-file=-
echo "your-plaid-production-secret" | gcloud secrets versions add sage-plaid-secret --data-file=-
```

#### Update Cloud Run Environment

```bash
# Set Plaid environment (sandbox or production)
gcloud run services update sage-backend \
  --update-env-vars PLAID_ENV=sandbox \
  --region us-central1
```

### 3. 🔧 Verify Deployment URLs

Check that your environment variables match your actual deployment URLs:

```bash
# Get your actual service URLs
BACKEND_URL=$(gcloud run services describe sage-backend --region=us-central1 --format='value(status.url)')
FRONTEND_URL=$(gcloud run services describe sage-frontend --region=us-central1 --format='value(status.url)')

echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
```

### 4. 🎯 Update OAuth Authorized Origins

Update your Google OAuth configuration with the actual frontend URL:

1. Go to [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials)
2. Click on your OAuth 2.0 Client ID
3. Add your actual frontend URL to:
   - Authorized JavaScript origins: `$FRONTEND_URL`
   - Authorized redirect URIs: `$FRONTEND_URL/auth/callback`

### 5. 🧪 Test Your Deployment

#### Backend Health Check
```bash
curl $BACKEND_URL/health
```

#### Frontend Health Check
```bash
curl $FRONTEND_URL/health
```

#### Test Authentication Flow
1. Visit your frontend URL: `$FRONTEND_URL`
2. Click "Sign in with Google"
3. Complete the OAuth flow
4. Verify you can access the dashboard

#### Test Plaid Integration (Sandbox)
1. After logging in, try to connect a bank account
2. Use Plaid's test credentials:
   - Username: `user_good`
   - Password: `pass_good`
3. Select "First Platypus Bank"
4. Verify accounts and transactions load

## 🔒 Security Best Practices

### Secret Management

- ✅ All sensitive data stored in Google Secret Manager
- ✅ No secrets in environment variables or code
- ✅ Firestore security rules enforced
- ✅ HTTPS-only communication

### OAuth Security

- ✅ Authorized origins limited to your domains
- ✅ Redirect URIs restricted to your application
- ✅ JWT tokens with configurable expiration
- ✅ User data isolation in Firestore

### Production Readiness

- ✅ Error monitoring enabled
- ✅ Budget alerts configured
- ✅ Health checks implemented
- ✅ Logging and monitoring active

## 🚨 Common Issues & Solutions

### OAuth Issues

**Problem:** "Error 400: redirect_uri_mismatch"
**Solution:** Verify your redirect URIs in Google OAuth configuration match exactly

**Problem:** "Error 403: access_denied"
**Solution:** Check if your OAuth consent screen is properly configured

### Plaid Issues

**Problem:** "invalid_client" error
**Solution:** Verify your Plaid client ID and secret are correct for the environment

**Problem:** Bank connection fails
**Solution:** Ensure you're using the correct Plaid environment (sandbox vs production)

### Deployment Issues

**Problem:** Services not accessible
**Solution:** Check that Cloud Run services are set to "Allow unauthenticated invocations"

**Problem:** CORS errors
**Solution:** Verify frontend URL is properly configured in backend environment variables

## 📞 Support

If you encounter issues:

1. **Check the logs:**
   ```bash
   # Backend logs
   gcloud logs read --service=sage-backend --limit=50
   
   # Frontend logs
   gcloud logs read --service=sage-frontend --limit=50
   ```

2. **Verify configuration:**
   ```bash
   # Check backend environment variables
   gcloud run services describe sage-backend --region=us-central1
   ```

3. **Test connectivity:**
   ```bash
   # Test backend health
   curl $BACKEND_URL/health
   
   # Test frontend health
   curl $FRONTEND_URL/health
   ```

## 🎉 You're Ready!

Once you've completed these steps:

1. ✅ Google OAuth is configured and working
2. ✅ Plaid integration is set up (sandbox or production)
3. ✅ All services are healthy and accessible
4. ✅ Users can sign in and connect bank accounts
5. ✅ Financial data is loading correctly

Your Sage Financial Management application is now fully operational!

**Next Steps:**
- Set up custom domain (optional)
- Configure additional Plaid products
- Customize the application for your needs
- Set up monitoring alerts
- Plan for scaling and backups