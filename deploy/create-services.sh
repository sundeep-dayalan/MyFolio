#!/bin/bash

# Create service accounts and configure IAM roles for Sage Financial Management App

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[SERVICE-SETUP]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SERVICE-SETUP]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[SERVICE-SETUP]${NC} $1"
}

log_error() {
    echo -e "${RED}[SERVICE-SETUP]${NC} $1"
}

# Check if PROJECT_ID is set
if [[ -z "$PROJECT_ID" ]]; then
    log_error "PROJECT_ID environment variable not set"
    exit 1
fi

log_info "Setting up service accounts and IAM roles for project: $PROJECT_ID"

# Service account names
BACKEND_SA="sage-backend-sa"
FRONTEND_SA="sage-frontend-sa"
DEPLOYMENT_SA="sage-deployment-sa"

# Function to create service account if it doesn't exist
create_service_account() {
    local sa_name=$1
    local display_name=$2
    local description=$3
    
    log_info "Creating service account: $sa_name"
    
    # Check if service account already exists
    if gcloud iam service-accounts describe "${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_warning "Service account $sa_name already exists, skipping creation"
        return 0
    fi
    
    # Create the service account
    if gcloud iam service-accounts create "$sa_name" \
        --display-name="$display_name" \
        --description="$description" \
        --project="$PROJECT_ID"; then
        log_success "✅ Service account $sa_name created"
        return 0
    else
        log_error "❌ Failed to create service account $sa_name"
        return 1
    fi
}

# Function to add IAM policy binding
add_iam_binding() {
    local sa_email=$1
    local role=$2
    local resource_type=${3:-"project"}
    
    log_info "Adding role $role to $sa_email"
    
    if [[ "$resource_type" == "project" ]]; then
        if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$sa_email" \
            --role="$role" \
            --quiet >/dev/null 2>&1; then
            log_success "✅ Role $role added to $sa_email"
            return 0
        else
            log_error "❌ Failed to add role $role to $sa_email"
            return 1
        fi
    fi
}

# ============================================================================
# CREATE SERVICE ACCOUNTS
# ============================================================================

log_info "Creating service accounts..."

# Backend service account
create_service_account "$BACKEND_SA" \
    "Sage Backend Service" \
    "Service account for Sage backend application running on Cloud Run"

# Frontend service account  
create_service_account "$FRONTEND_SA" \
    "Sage Frontend Service" \
    "Service account for Sage frontend application running on Cloud Run"

# Deployment service account
create_service_account "$DEPLOYMENT_SA" \
    "Sage Deployment Service" \
    "Service account for deployment and CI/CD operations"

echo ""

# ============================================================================
# CONFIGURE IAM ROLES
# ============================================================================

log_info "Configuring IAM roles..."

# Backend service account permissions
BACKEND_SA_EMAIL="${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

log_info "Configuring backend service account permissions..."
add_iam_binding "$BACKEND_SA_EMAIL" "roles/firestore.user"
add_iam_binding "$BACKEND_SA_EMAIL" "roles/firebase.admin"
add_iam_binding "$BACKEND_SA_EMAIL" "roles/secretmanager.secretAccessor"
add_iam_binding "$BACKEND_SA_EMAIL" "roles/logging.logWriter"
add_iam_binding "$BACKEND_SA_EMAIL" "roles/monitoring.metricWriter"
add_iam_binding "$BACKEND_SA_EMAIL" "roles/cloudtrace.agent"

# Frontend service account permissions  
FRONTEND_SA_EMAIL="${FRONTEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

log_info "Configuring frontend service account permissions..."
add_iam_binding "$FRONTEND_SA_EMAIL" "roles/logging.logWriter"
add_iam_binding "$FRONTEND_SA_EMAIL" "roles/monitoring.metricWriter"

# Deployment service account permissions
DEPLOYMENT_SA_EMAIL="${DEPLOYMENT_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

log_info "Configuring deployment service account permissions..."
add_iam_binding "$DEPLOYMENT_SA_EMAIL" "roles/run.admin"
add_iam_binding "$DEPLOYMENT_SA_EMAIL" "roles/cloudbuild.builds.builder"
add_iam_binding "$DEPLOYMENT_SA_EMAIL" "roles/storage.admin"
add_iam_binding "$DEPLOYMENT_SA_EMAIL" "roles/iam.serviceAccountUser"
add_iam_binding "$DEPLOYMENT_SA_EMAIL" "roles/artifactregistry.admin"

echo ""

# ============================================================================
# CREATE SECRETS IN SECRET MANAGER
# ============================================================================

log_info "Setting up Secret Manager secrets..."

# Function to create secret if it doesn't exist
create_secret() {
    local secret_name=$1
    local secret_value=$2
    
    log_info "Creating secret: $secret_name"
    
    # Check if secret already exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_warning "Secret $secret_name already exists, skipping creation"
        return 0
    fi
    
    # Create the secret
    if echo -n "$secret_value" | gcloud secrets create "$secret_name" \
        --data-file=- \
        --project="$PROJECT_ID"; then
        log_success "✅ Secret $secret_name created"
        return 0
    else
        log_error "❌ Failed to create secret $secret_name"
        return 1
    fi
}

# Create placeholder secrets (users will need to update these)
create_secret "sage-jwt-secret" "$(openssl rand -base64 32)"
create_secret "sage-plaid-client-id" "REPLACE_WITH_YOUR_PLAID_CLIENT_ID"
create_secret "sage-plaid-secret" "REPLACE_WITH_YOUR_PLAID_SECRET"
create_secret "sage-google-oauth-client-id" "REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID"
create_secret "sage-google-oauth-client-secret" "REPLACE_WITH_YOUR_GOOGLE_CLIENT_SECRET"

# Grant secret access to backend service account
log_info "Granting secret access to backend service account..."
for secret in "sage-jwt-secret" "sage-plaid-client-id" "sage-plaid-secret" "sage-google-oauth-client-id" "sage-google-oauth-client-secret"; do
    gcloud secrets add-iam-policy-binding "$secret" \
        --member="serviceAccount:$BACKEND_SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor" \
        --project="$PROJECT_ID" >/dev/null 2>&1
done

echo ""

# ============================================================================
# CONFIGURE CLOUD MONITORING
# ============================================================================

log_info "Setting up monitoring and alerting..."

# Create notification channel for budget alerts (email)
if [[ -n "$USER_EMAIL" ]]; then
    log_info "Creating email notification channel for budget alerts..."
    
    # Create notification channel configuration
    cat > /tmp/notification-channel.json << EOF
{
  "type": "email",
  "displayName": "Sage Budget Alerts",
  "description": "Email notifications for Sage app budget alerts",
  "labels": {
    "email_address": "$USER_EMAIL"
  }
}
EOF

    # Create the notification channel
    if gcloud alpha monitoring channels create --channel-content-from-file=/tmp/notification-channel.json --project="$PROJECT_ID" >/dev/null 2>&1; then
        log_success "✅ Email notification channel created"
    else
        log_warning "⚠️  Could not create notification channel (may already exist)"
    fi
    
    rm -f /tmp/notification-channel.json
fi

echo ""

# ============================================================================
# SETUP BUDGET ALERTS
# ============================================================================

log_info "Setting up budget alerts..."

# Create budget for cost monitoring
cat > /tmp/budget.json << EOF
{
  "displayName": "Sage App Budget",
  "budgetFilter": {
    "projects": ["projects/$PROJECT_ID"]
  },
  "amount": {
    "specifiedAmount": {
      "currencyCode": "USD",
      "units": 10
    }
  },
  "thresholdRules": [
    {
      "thresholdPercent": 0.5,
      "spendBasis": "CURRENT_SPEND"
    },
    {
      "thresholdPercent": 0.8,
      "spendBasis": "CURRENT_SPEND"
    },
    {
      "thresholdPercent": 1.0,
      "spendBasis": "CURRENT_SPEND"
    }
  ]
}
EOF

# Create the budget
if gcloud billing budgets create --billing-account="$(gcloud billing projects describe $PROJECT_ID --format='value(billingAccountName)' | cut -d'/' -f2)" --budget-from-file=/tmp/budget.json >/dev/null 2>&1; then
    log_success "✅ Budget alert created (\$10 monthly limit)"
else
    log_warning "⚠️  Could not create budget alert (billing account may not be accessible)"
fi

rm -f /tmp/budget.json

echo ""

# ============================================================================
# CREATE DEFAULT FIRESTORE SECURITY RULES
# ============================================================================

log_info "Setting up Firestore security rules..."

# Create default security rules
cat > /tmp/firestore.rules << 'EOF'
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read and write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      
      // Users can read and write their own accounts
      match /accounts/{accountId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
      
      // Users can read and write their own transactions
      match /transactions/{transactionId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
    
    // Deny all other access
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
EOF

# Deploy Firestore rules
if gcloud firestore deploy --rules=/tmp/firestore.rules --project="$PROJECT_ID" >/dev/null 2>&1; then
    log_success "✅ Firestore security rules deployed"
else
    log_warning "⚠️  Could not deploy Firestore security rules"
fi

rm -f /tmp/firestore.rules

echo ""

# ============================================================================
# SUMMARY
# ============================================================================

log_success "🎉 Service setup completed successfully!"

echo ""
echo "📋 Summary of created resources:"
echo ""
echo "🔐 Service Accounts:"
echo "  - $BACKEND_SA_EMAIL (Backend application)"
echo "  - $FRONTEND_SA_EMAIL (Frontend application)"  
echo "  - $DEPLOYMENT_SA_EMAIL (Deployment operations)"
echo ""
echo "🔑 Secrets (in Secret Manager):"
echo "  - sage-jwt-secret (Auto-generated)"
echo "  - sage-plaid-client-id (Needs update)"
echo "  - sage-plaid-secret (Needs update)"
echo "  - sage-google-oauth-client-id (Needs update)"
echo "  - sage-google-oauth-client-secret (Needs update)"
echo ""
echo "📊 Monitoring:"
echo "  - Budget alert set to \$10/month"
echo "  - Email notifications to: ${USER_EMAIL:-'Not configured'}"
echo "  - Cloud Logging enabled"
echo ""
echo "🗄️  Database:"
echo "  - Firestore security rules deployed"
echo "  - User data isolation configured"
echo ""

log_warning "⚠️  Important: Update the placeholder secrets with your actual API credentials after deployment!"

echo ""
log_success "🚀 Ready for application deployment!"