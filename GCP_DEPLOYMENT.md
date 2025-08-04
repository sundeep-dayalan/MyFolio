# MyFolio FastAPI - Google Cloud Platform Deployment Guide

This guide will help you deploy your FastAPI application to Google Cloud Platform using Cloud Run.

## Prerequisites

1. **Google Cloud Platform Account**
   - Create a GCP account if you don't have one
   - Create a new project or use an existing one

2. **Local Tools**
   - Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
   - Install [Docker](https://docs.docker.com/get-docker/)
   - Ensure you have Python 3.11+ installed

## Quick Deployment (Automated)

### Option 1: Using the Deploy Script

1. **Setup your GCP project**:
   ```bash
   # Authenticate with Google Cloud
   gcloud auth login
   
   # Set your project ID (replace with your actual project ID)
   export PROJECT_ID="your-project-id"
   gcloud config set project $PROJECT_ID
   ```

2. **Update the deploy script**:
   - Open `api/deploy.sh`
   - Update the `PROJECT_ID` variable with your actual GCP project ID

3. **Make the script executable and run it**:
   ```bash
   cd api
   chmod +x deploy.sh
   ./deploy.sh
   ```

   The script will:
   - Enable required GCP APIs
   - Build and push your Docker image
   - Create secrets in Secret Manager
   - Deploy to Cloud Run
   - Provide you with the deployment URL

### Option 2: Using Cloud Build (Recommended for Production)

1. **Setup Cloud Build**:
   ```bash
   # Enable Cloud Build API
   gcloud services enable cloudbuild.googleapis.com
   
   # Trigger a build
   gcloud builds submit --config=cloudbuild.yaml
   ```

## Manual Deployment Steps

### Step 1: Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### Step 2: Create Secrets in Secret Manager

```bash
# Create secrets for sensitive data
echo -n "your-secret-key-here" | gcloud secrets create SECRET_KEY --data-file=-
echo -n "your-google-client-id" | gcloud secrets create GOOGLE_CLIENT_ID --data-file=-
echo -n "your-google-client-secret" | gcloud secrets create GOOGLE_CLIENT_SECRET --data-file=-
echo -n "your-firebase-project-id" | gcloud secrets create FIREBASE_PROJECT_ID --data-file=-

# Upload Firebase service account JSON
gcloud secrets create FIREBASE_CREDENTIALS --data-file=service-account.json
```

### Step 3: Build and Push Docker Image

```bash
# Build the image
docker build -t gcr.io/$PROJECT_ID/myfolio-api .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/myfolio-api
```

### Step 4: Deploy to Cloud Run

```bash
gcloud run deploy myfolio-api \
  --image gcr.io/$PROJECT_ID/myfolio-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production,DEBUG=false \
  --set-secrets SECRET_KEY=SECRET_KEY:latest \
  --set-secrets GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest \
  --set-secrets GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest \
  --set-secrets FIREBASE_PROJECT_ID=FIREBASE_PROJECT_ID:latest \
  --set-secrets FIREBASE_CREDENTIALS=FIREBASE_CREDENTIALS:latest
```

## CI/CD with GitHub Actions

### Setup GitHub Secrets

In your GitHub repository, go to Settings > Secrets and Variables > Actions, and add:

1. `GCP_PROJECT_ID` - Your Google Cloud Project ID
2. `GCP_SA_KEY` - Service Account JSON key (see below for creation)

### Create Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Service Account"

# Get the service account email
SA_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:GitHub Actions Service Account" \
  --format="value(email)")

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudbuild.builds.editor"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=$SA_EMAIL

# Copy the content of github-actions-key.json to GCP_SA_KEY secret in GitHub
```

## Post-Deployment Configuration

### 1. Update Google OAuth Settings

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services > Credentials
3. Edit your OAuth 2.0 Client ID
4. Add your Cloud Run URL to authorized redirect URIs:
   - `https://your-service-url/api/v1/auth/oauth/google/callback`

### 2. Update CORS Settings

Update your frontend application to use the new Cloud Run URL for API calls.

### 3. Update Environment Variables (if needed)

```bash
# Update service with new environment variables
gcloud run services update myfolio-api \
  --region us-central1 \
  --set-env-vars NEW_VARIABLE=value
```

## Monitoring and Troubleshooting

### View Logs

```bash
# View real-time logs
gcloud logs tail -s gcloud-run --service myfolio-api --region us-central1

# View recent logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=myfolio-api" --limit 50
```

### Health Check

Your application includes a health check endpoint at `/health`. You can test it:

```bash
curl https://your-service-url/health
```

### Common Issues

1. **Cold Starts**: First request might be slow due to cold start
   - Solution: Configure minimum instances if needed

2. **Memory Issues**: If you see out-of-memory errors
   - Solution: Increase memory allocation in deployment

3. **Timeout Issues**: For long-running requests
   - Solution: Increase timeout settings in Cloud Run

4. **Firebase Connection Issues**: Check if service account has proper permissions
   - Solution: Verify Firebase service account JSON and project ID

## Security Best Practices

1. **Use Secret Manager**: Never hardcode secrets in your code
2. **Limit Access**: Use IAM to control who can access your services
3. **Enable Audit Logs**: Monitor access to your application
4. **Use HTTPS**: Cloud Run provides HTTPS by default
5. **Regular Updates**: Keep your dependencies updated

## Cost Optimization

1. **Right-size Resources**: Start with minimal CPU/memory and scale up if needed
2. **Set Max Instances**: Prevent runaway costs with instance limits
3. **Use Regional Resources**: Choose regions closest to your users
4. **Monitor Usage**: Use Cloud Monitoring to track resource usage

## Support

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)

For application-specific issues, check the application logs and health endpoint.
