# GitHub Actions Deployment Setup

## Required GitHub Secrets

To enable automatic deployment, you need to add these secrets to your GitHub repository:

### 1. Go to your GitHub repository
- Navigate to: `Settings` → `Secrets and variables` → `Actions`

### 2. Add Repository Secrets

| Secret Name | Value | Description |
|-------------|--------|-------------|
| `GCP_PROJECT_ID` | `fit-guide-465001-p3` | Your Google Cloud Project ID |
| `GCP_SA_KEY` | `<service-account-json>` | Base64 encoded service account JSON |
| `SECRET_KEY` | `<your-secret-key>` | JWT secret key for the API |
| `GOOGLE_CLIENT_ID` | `<your-client-id>` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | `<your-client-secret>` | Google OAuth client secret |
| `FIREBASE_PROJECT_ID` | `fit-guide-465001-p3` | Firebase project ID |
| `FIREBASE_CREDENTIALS` | `<service-account-json>` | Firebase service account JSON |

### 3. Get Service Account Key

Run this command to get the base64 encoded service account key:

```bash
# Get the service account key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=myfolio-api-service@fit-guide-465001-p3.iam.gserviceaccount.com

# Encode it for GitHub secrets
base64 -i github-actions-key.json

# Copy the output and paste it as GCP_SA_KEY in GitHub secrets
```

### 4. Get Google OAuth Credentials

```bash
# Get Google OAuth credentials from Secret Manager
gcloud secrets versions access latest --secret="GOOGLE_CLIENT_ID"
gcloud secrets versions access latest --secret="GOOGLE_CLIENT_SECRET"
```

### 5. Get Secret Key

```bash
# Get the secret key from Secret Manager
gcloud secrets versions access latest --secret="SECRET_KEY"
```

### 6. Get Firebase Credentials

```bash
# Get Firebase credentials from Secret Manager
gcloud secrets versions access latest --secret="FIREBASE_CREDENTIALS"
```

## How It Works

Once you set up the secrets:

1. **Push changes** to the `api/` folder on the `main` branch
2. **GitHub Actions automatically**:
   - Runs tests
   - Builds Docker image
   - Pushes to Google Container Registry
   - Deploys to Cloud Run
   - Runs health checks

## Workflow Triggers

The deployment runs when:
- ✅ Push to `main` branch with changes in `api/` folder
- ✅ Manual trigger via GitHub Actions UI
- 🔄 Pull request (runs tests only, no deployment)

## Monitoring

After setup, you can monitor deployments at:
- GitHub: `Actions` tab in your repository
- GCP: Cloud Run console for service logs
- API: `https://myfolio-api-681015953939.us-central1.run.app/health`
