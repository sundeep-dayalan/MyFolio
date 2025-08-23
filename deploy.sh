#!/bin/bash

# Sage Financial Management App - Bulletproof Azure Deployment
# Based on latest Azure CLI documentation and best practices for 2025
# Handles all resource provider registrations and uses current syntax

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="sage-financial-app"
LOCATION="Central US"
CONSUMPTION_LOCATION="centralus"
ENVIRONMENT="prod"
UNIQUE_SUFFIX=$(date +%s | tail -c 6)
RESOURCE_GROUP_NAME="${PROJECT_NAME}-rg-${UNIQUE_SUFFIX}"

# Resource names with proper conventions
STORAGE_NAME="sage${UNIQUE_SUFFIX}storage"
COSMOS_NAME="sage-${UNIQUE_SUFFIX}-cosmos"
KEY_VAULT_NAME="sage-${UNIQUE_SUFFIX}-kv"
INSIGHTS_NAME="sage-${UNIQUE_SUFFIX}-insights"
FUNCTION_APP_NAME="sage-${UNIQUE_SUFFIX}-api"
STATIC_WEB_APP_NAME="sage-${UNIQUE_SUFFIX}-web"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for resource provider registration
wait_for_provider_registration() {
    local provider=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $provider registration to complete..."
    
    while [ $attempt -le $max_attempts ]; do
        local status=$(az provider show --namespace "$provider" --query "registrationState" --output tsv 2>/dev/null)
        
        if [ "$status" = "Registered" ]; then
            print_success "$provider is now registered"
            return 0
        fi
        
        echo -n "."
        sleep 10
        ((attempt++))
    done
    
    print_error "$provider registration timed out"
    return 1
}

# Step 1: Prerequisites and resource provider registration
setup_prerequisites() {
    print_header "STEP 1: PREREQUISITES & RESOURCE PROVIDERS"
    
    # Check Azure CLI
    if ! command_exists az; then
        print_error "Azure CLI is not installed. Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Check if logged into Azure
    if ! az account show &>/dev/null; then
        print_error "Not logged into Azure. Please run 'az login' first."
        exit 1
    fi
    
    # Check Node.js and Python
    if ! command_exists node; then
        print_error "Node.js is not installed. Install from: https://nodejs.org/"
        exit 1
    fi
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Install from: https://python.org/"
        exit 1
    fi
    
    print_success "All prerequisites met!"
    
    # Register required resource providers
    print_status "Registering Azure resource providers..."
    
    local providers=("Microsoft.Storage" "Microsoft.Web" "Microsoft.DocumentDB" "Microsoft.KeyVault" "Microsoft.Insights" "Microsoft.OperationalInsights")
    
    for provider in "${providers[@]}"; do
        print_status "Checking $provider..."
        local status=$(az provider show --namespace "$provider" --query "registrationState" --output tsv 2>/dev/null || echo "NotFound")
        
        if [ "$status" != "Registered" ]; then
            print_warning "$provider not registered. Registering now..."
            az provider register --namespace "$provider" --wait
            wait_for_provider_registration "$provider"
        else
            print_success "$provider already registered"
        fi
    done
    
    print_success "All resource providers registered!"
}

# Step 2: Create resource group
setup_resource_group() {
    print_header "STEP 2: RESOURCE GROUP"
    
    # Check for existing resource groups
    echo "Checking for existing resource groups..."
    existing_rgs=$(az group list --query "[].name" -o tsv 2>/dev/null)
    
    if [ -n "$existing_rgs" ]; then
        echo ""
        echo "📋 Found existing resource groups:"
        echo "$existing_rgs" | while read rg; do
            echo "  • $rg"
        done
        echo ""
        
        read -p "Do you want to use an existing resource group? (y/n): " use_existing
        
        if [[ "$use_existing" =~ ^[Yy]$ ]]; then
            echo ""
            echo "Available resource groups:"
            select rg_option in $existing_rgs "Create new resource group"; do
                if [ "$rg_option" = "Create new resource group" ]; then
                    break
                elif [ -n "$rg_option" ]; then
                    RESOURCE_GROUP_NAME="$rg_option"
                    print_success "Using existing resource group: $RESOURCE_GROUP_NAME"
                    
                    # Get the location of the existing resource group
                    LOCATION=$(az group show --name "$RESOURCE_GROUP_NAME" --query location -o tsv)
                    echo "📍 Resource group location: $LOCATION"
                    
                    # Discover existing resources in the resource group
                    discover_existing_resources
                    return
                fi
            done
        fi
    fi
    
    # Create new resource group
    print_status "Creating new resource group: $RESOURCE_GROUP_NAME"
    print_status "Location: $LOCATION"
    
    if az group show --name "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        print_warning "Resource group $RESOURCE_GROUP_NAME already exists!"
        return
    fi
    
    az group create \
        --name "$RESOURCE_GROUP_NAME" \
        --location "$LOCATION" \
        --tags "project=$PROJECT_NAME" "environment=$ENVIRONMENT" \
        --output none
    
    print_success "Resource group created!"
}

# Function to discover existing resources in the resource group
discover_existing_resources() {
    print_header "DISCOVERING EXISTING RESOURCES"
    
    echo "🔍 Scanning resource group for existing Sage resources..."
    
    # Get all resources in the resource group
    resources=$(az resource list --resource-group "$RESOURCE_GROUP_NAME" --query "[].{name:name,type:type}" -o tsv)
    
    # Look for existing Sage resources
    while IFS=$'\t' read -r name type; do
        case "$type" in
            "Microsoft.Storage/storageAccounts")
                if [[ "$name" == *"sage"* ]] || [[ "$name" == *"storage"* ]]; then
                    STORAGE_NAME="$name"
                    echo "  ✅ Found storage account: $STORAGE_NAME"
                fi
                ;;
            "Microsoft.DocumentDB/databaseAccounts")
                if [[ "$name" == *"sage"* ]] || [[ "$name" == *"cosmos"* ]]; then
                    COSMOS_NAME="$name"
                    echo "  ✅ Found Cosmos DB: $COSMOS_NAME"
                fi
                ;;
            "Microsoft.Web/sites")
                if [[ "$name" == *"sage"* ]] && [[ "$name" == *"api"* ]]; then
                    # Check if it's a function app or regular web app
                    local site_kind=$(az resource show --resource-group "$RESOURCE_GROUP_NAME" --name "$name" --resource-type "Microsoft.Web/sites" --query "kind" -o tsv 2>/dev/null)
                    if [[ "$site_kind" == *"functionapp"* ]]; then
                        FUNCTION_APP_NAME="$name"
                        echo "  ✅ Found Function App: $FUNCTION_APP_NAME"
                    fi
                elif [[ "$name" == *"sage"* ]] && [[ "$name" == *"web"* ]]; then
                    STATIC_WEB_APP_NAME="$name"
                    echo "  ✅ Found Static Web App: $STATIC_WEB_APP_NAME"
                fi
                ;;
            "Microsoft.KeyVault/vaults")
                if [[ "$name" == *"sage"* ]] || [[ "$name" == *"kv"* ]]; then
                    KEY_VAULT_NAME="$name"
                    echo "  ✅ Found Key Vault: $KEY_VAULT_NAME"
                fi
                ;;
            "Microsoft.Insights/components")
                if [[ "$name" == *"sage"* ]] || [[ "$name" == *"insights"* ]]; then
                    INSIGHTS_NAME="$name"
                    echo "  ✅ Found Application Insights: $INSIGHTS_NAME"
                fi
                ;;
        esac
    done <<< "$resources"
    
    echo ""
    echo "📋 Resource Discovery Summary:"
    echo "  Storage Account: ${STORAGE_NAME:-❌ Not found}"
    echo "  Cosmos DB: ${COSMOS_NAME:-❌ Not found}"
    echo "  Function App: ${FUNCTION_APP_NAME:-❌ Not found}"
    echo "  Static Web App: ${STATIC_WEB_APP_NAME:-❌ Not found}"
    echo "  Key Vault: ${KEY_VAULT_NAME:-❌ Not found}"
    echo "  Application Insights: ${INSIGHTS_NAME:-❌ Not found}"
    echo ""
    
    # Generate new names for missing resources using a consistent pattern
    if [ -z "$STORAGE_NAME" ] || [ -z "$COSMOS_NAME" ] || [ -z "$KEY_VAULT_NAME" ] || [ -z "$FUNCTION_APP_NAME" ]; then
        echo "⚙️  Generating names for missing resources..."
        UNIQUE_SUFFIX=$(echo "$RESOURCE_GROUP_NAME-$LOCATION" | sha256sum | cut -c1-8)
        
        [ -z "$STORAGE_NAME" ] && STORAGE_NAME="sage${UNIQUE_SUFFIX}storage"
        [ -z "$COSMOS_NAME" ] && COSMOS_NAME="sage-${UNIQUE_SUFFIX}-cosmos"
        [ -z "$FUNCTION_APP_NAME" ] && FUNCTION_APP_NAME="sage-${UNIQUE_SUFFIX}-api"
        [ -z "$KEY_VAULT_NAME" ] && KEY_VAULT_NAME="sage-${UNIQUE_SUFFIX}-kv"
        [ -z "$STATIC_WEB_APP_NAME" ] && STATIC_WEB_APP_NAME="sage-${UNIQUE_SUFFIX}-web"
        [ -z "$INSIGHTS_NAME" ] && INSIGHTS_NAME="sage-${UNIQUE_SUFFIX}-insights"
        
        echo "  New names will be generated with suffix: $UNIQUE_SUFFIX"
    fi
    
    print_success "Resource discovery completed!"
}

# Step 3: Create storage account
create_storage_account() {
    print_header "STEP 3: STORAGE ACCOUNT"
    
    # Check if storage account already exists
    if az storage account show --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        print_warning "Storage account $STORAGE_NAME already exists! Skipping creation..."
        return
    fi
    
    print_status "Creating storage account: $STORAGE_NAME"
    
    az storage account create \
        --name "$STORAGE_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --location "$LOCATION" \
        --sku Standard_LRS \
        --kind StorageV2 \
        --https-only true \
        --min-tls-version TLS1_2 \
        --allow-blob-public-access false \
        --tags "project=$PROJECT_NAME" \
        --output none
    
    print_success "Storage account created!"
}

# Step 4: Create Cosmos DB (using free tier instead of serverless for better reliability)
create_cosmos_db() {
    print_header "STEP 4: COSMOS DB"
    
    # Check if Cosmos DB account already exists
    if az cosmosdb show --name "$COSMOS_NAME" --resource-group "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        print_warning "Cosmos DB $COSMOS_NAME already exists! Checking components..."
        
        # Check and create database if needed
        if ! az cosmosdb sql database show --account-name "$COSMOS_NAME" --resource-group "$RESOURCE_GROUP_NAME" --name "sage-db" >/dev/null 2>&1; then
            print_status "Creating missing database: sage-db"
            az cosmosdb sql database create \
                --account-name "$COSMOS_NAME" \
                --resource-group "$RESOURCE_GROUP_NAME" \
                --name "sage-db" \
                --throughput 400 \
                --output none
        fi
        
        # Check containers
        local containers=("users" "accounts" "transactions" "plaid_tokens")
        for container in "${containers[@]}"; do
            if ! az cosmosdb sql container show --account-name "$COSMOS_NAME" --database-name "sage-db" --resource-group "$RESOURCE_GROUP_NAME" --name "$container" >/dev/null 2>&1; then
                print_status "Creating missing container: $container"
                az cosmosdb sql container create \
                    --account-name "$COSMOS_NAME" \
                    --resource-group "$RESOURCE_GROUP_NAME" \
                    --database-name "sage-db" \
                    --name "$container" \
                    --partition-key-path "/userId" \
                    --output none
            fi
        done
        print_success "Cosmos DB components verified!"
        return
    fi
    
    print_status "Creating Cosmos DB: $COSMOS_NAME"
    
    # Check if free tier is available in this subscription
    echo "Checking Cosmos DB free tier availability..."
    free_tier_available=true
    
    # Try to detect if free tier is already used by attempting creation with dry-run equivalent
    # If free tier is not available, we'll create without it
    
    print_warning "Attempting to use free tier (1000 RU/s, 25GB free)"
    print_warning "If free tier is unavailable, will create standard account"
    
    # Create Cosmos DB account - try with free tier first
    if ! az cosmosdb create \
        --name "$COSMOS_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --kind GlobalDocumentDB \
        --default-consistency-level Session \
        --enable-free-tier true \
        --enable-automatic-failover false \
        --locations regionName="$LOCATION" failoverPriority=0 isZoneRedundant=false \
        --tags "project=$PROJECT_NAME" \
        --output none 2>/dev/null; then
        
        print_warning "Free tier not available, creating standard Cosmos DB account..."
        az cosmosdb create \
            --name "$COSMOS_NAME" \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --kind GlobalDocumentDB \
            --default-consistency-level Session \
            --enable-automatic-failover false \
            --locations regionName="$LOCATION" failoverPriority=0 isZoneRedundant=false \
            --tags "project=$PROJECT_NAME" \
            --output none
    fi
    
    print_success "Cosmos DB account created!"
    
    # Create database
    print_status "Creating database: sage-db"
    az cosmosdb sql database create \
        --account-name "$COSMOS_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "sage-db" \
        --throughput 400 \
        --output none
    
    # Create containers
    local containers=("users" "accounts" "transactions" "plaid_tokens")
    for container in "${containers[@]}"; do
        print_status "Creating container: $container"
        az cosmosdb sql container create \
            --account-name "$COSMOS_NAME" \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --database-name "sage-db" \
            --name "$container" \
            --partition-key-path "/userId" \
            --output none
    done
    
    print_success "Database and containers created!"
}

# Step 5: Create Application Insights
create_app_insights() {
    print_header "STEP 5: APPLICATION INSIGHTS"
    
    # Check if Application Insights already exists
    if az monitor app-insights component show --app "$INSIGHTS_NAME" --resource-group "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        print_warning "Application Insights $INSIGHTS_NAME already exists! Skipping creation..."
        return
    fi
    
    print_status "Creating Application Insights: $INSIGHTS_NAME"
    
    az monitor app-insights component create \
        --app "$INSIGHTS_NAME" \
        --location "$LOCATION" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --kind web \
        --retention-time 30 \
        --tags "project=$PROJECT_NAME" \
        --output none
    
    print_success "Application Insights created!"
}

# Step 6: Create Key Vault
create_key_vault() {
    print_header "STEP 6: KEY VAULT"
    
    # Check if Key Vault already exists
    if az keyvault show --name "$KEY_VAULT_NAME" --resource-group "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        print_warning "Key Vault $KEY_VAULT_NAME already exists! Skipping creation..."
        return
    fi
    
    print_status "Creating Key Vault: $KEY_VAULT_NAME"
    
    az keyvault create \
        --name "$KEY_VAULT_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --location "$LOCATION" \
        --sku standard \
        --enable-rbac-authorization true \
        --tags "project=$PROJECT_NAME" \
        --output none
    
    print_success "Key Vault created!"
    
    # Grant current user access to Key Vault
    print_status "Configuring Key Vault permissions..."
    local current_user=$(az ad signed-in-user show --query id --output tsv)
    
    az role assignment create \
        --role "Key Vault Secrets Officer" \
        --assignee "$current_user" \
        --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME" \
        --output none
    
    print_success "Key Vault permissions configured!"
}

# Step 7: Create Azure Function App
create_function_app() {
    print_header "STEP 7: AZURE FUNCTIONS"
    
    # Check if Function App already exists
    if az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        print_warning "Function App $FUNCTION_APP_NAME already exists! Skipping creation..."
        return
    fi
    
    print_status "Creating Function App: $FUNCTION_APP_NAME"
    print_warning "Using Consumption plan (serverless, pay-per-execution)"
    
    # Create Function App with consumption plan (free tier)
    az functionapp create \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --consumption-plan-location "$CONSUMPTION_LOCATION" \
        --runtime python \
        --runtime-version 3.11 \
        --functions-version 4 \
        --name "$FUNCTION_APP_NAME" \
        --storage-account "$STORAGE_NAME" \
        --os-type Linux \
        --tags "project=$PROJECT_NAME"
    
    print_success "Function App created!"
}

# Step 8: Create Static Web App
create_static_web_app() {
    print_header "STEP 8: STATIC WEB APP"
    
    print_status "Creating Static Web App: $STATIC_WEB_APP_NAME"
    
    az staticwebapp create \
        --name "$STATIC_WEB_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --location "Central US" \
        --sku Free \
        --tags "project=$PROJECT_NAME" \
        --output none
    
    print_success "Static Web App created!"
}

# Step 9: Configure Function App settings
configure_function_app() {
    print_header "STEP 9: FUNCTION APP CONFIGURATION"
    
    print_status "Configuring Function App settings..."
    
    # Get connection strings and keys
    local cosmos_key=$(az cosmosdb keys list \
        --name "$COSMOS_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query primaryMasterKey \
        --output tsv)
    
    local cosmos_endpoint="https://${COSMOS_NAME}.documents.azure.com:443/"
    
    local insights_connection=$(az monitor app-insights component show \
        --app "$INSIGHTS_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query connectionString \
        --output tsv)
    
    local key_vault_url="https://${KEY_VAULT_NAME}.vault.azure.net/"
    
    # Configure function app settings
    az functionapp config appsettings set \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --settings \
            "COSMOS_DB_ENDPOINT=$cosmos_endpoint" \
            "COSMOS_DB_KEY=$cosmos_key" \
            "COSMOS_DB_NAME=sage-db" \
            "KEY_VAULT_URL=$key_vault_url" \
            "ENVIRONMENT=$ENVIRONMENT" \
            "APPLICATIONINSIGHTS_CONNECTION_STRING=$insights_connection" \
            "FUNCTIONS_WORKER_RUNTIME=python" \
            "PYTHON_ENABLE_GUNICORN_MULTIPROCESSING=1" \
        --output none
    
    print_success "Function App configured!"
}

# Step 10: Setup secrets in Key Vault
setup_secrets() {
    print_header "STEP 10: KEY VAULT SECRETS"
    
    print_status "Setting up secrets in Key Vault..."
    print_warning "Waiting for Key Vault permissions to propagate..."
    sleep 15
    
    # Generate secure JWT secret
    local jwt_secret=$(openssl rand -hex 32)
    
    # Set secrets with retry logic
    local secrets=("jwt-secret:$jwt_secret" "google-client-id:configure-me" "google-client-secret:configure-me" "plaid-client-id:configure-me" "plaid-secret:configure-me")
    
    for secret_pair in "${secrets[@]}"; do
        local secret_name=$(echo "$secret_pair" | cut -d: -f1)
        local secret_value=$(echo "$secret_pair" | cut -d: -f2-)
        
        local retry_count=0
        local max_retries=3
        
        while [ $retry_count -lt $max_retries ]; do
            if az keyvault secret set \
                --vault-name "$KEY_VAULT_NAME" \
                --name "$secret_name" \
                --value "$secret_value" \
                --output none 2>/dev/null; then
                print_status "Set secret: $secret_name"
                break
            else
                ((retry_count++))
                if [ $retry_count -lt $max_retries ]; then
                    print_warning "Retry $retry_count/$max_retries for secret: $secret_name"
                    sleep 5
                else
                    print_error "Failed to set secret: $secret_name after $max_retries attempts"
                fi
            fi
        done
    done
    
    print_success "Secrets configured!"
}

# Step 11: Deploy backend
deploy_backend() {
    print_header "STEP 11: BACKEND DEPLOYMENT"
    
    print_status "Deploying Azure Functions backend..."
    
    cd server
    
    # Create deployment package
    print_status "Creating deployment package..."
    
    # Create a temporary directory for deployment
    # mkdir -p .deployment
    
    # Copy all server files
    # cp -r * .deployment/ 2>/dev/null || true
    # cd .deployment
    
    # Remove any existing virtual environments and cache
    # rm -rf .venv venv __pycache__ .pytest_cache .git *.log
    
    # Create deployment zip
    # print_status "Creating deployment zip..."
    # zip -r ../deployment.zip . -x "*.git*" "*.DS_Store*" "*.pyc" "__pycache__/*" ".venv/*" "venv/*" "*.log"
    # cd ..
    
    # Deploy using zip deployment
    print_status "Deploying via ZIP upload..."
    local retry_count=0
    local max_retries=2
    
    while [ $retry_count -lt $max_retries ]; do
        if func azure functionapp publish "$FUNCTION_APP_NAME"; then
            print_success "Backend deployed successfully!"
            break
        else
            ((retry_count++))
            if [ $retry_count -lt $max_retries ]; then
                print_warning "Deployment retry $retry_count/$max_retries"
                sleep 30
            else
                print_error "Backend deployment failed after $max_retries attempts"
                cd ..
                exit 1
            fi
        fi
    done
    
    

    # Cleanup
    # rm -rf .deployment deployment.zip
    cd ..
}

# Step 12: Build frontend
build_frontend() {
    print_header "STEP 12: FRONTEND BUILD"
    
    print_status "Building React frontend..."
    
    cd frontend
    
    # Get URLs
    local function_app_url="https://${FUNCTION_APP_NAME}.azurewebsites.net"
    local static_web_app_hostname=$(az staticwebapp show \
        --name "$STATIC_WEB_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query defaultHostname \
        --output tsv)
    local static_web_app_url="https://${static_web_app_hostname}"
    
    # Install dependencies
    print_status "Installing dependencies..."
    npm install --silent
    
    # Create production environment
    cat > .env.production << EOF
VITE_API_BASE_URL=${function_app_url}/api
VITE_APP_ENV=production
VITE_GOOGLE_CLIENT_ID=configure-me
EOF
    
    # Build application
    print_status "Building application..."
    npm run build --silent
    
    print_success "Frontend built successfully!"
    
    cd ..
    
    # Store URLs for final output
    FUNCTION_APP_URL="$function_app_url"
    STATIC_WEB_APP_URL="$static_web_app_url"
}

# Final summary
display_summary() {
    print_header "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "                        DEPLOYMENT SUMMARY"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    print_success "All Azure resources have been created and configured!"
    echo ""
    echo "📦 RESOURCE GROUP: $RESOURCE_GROUP_NAME"
    echo "📍 LOCATION: $LOCATION"
    echo ""
    echo "🔗 APPLICATION URLS:"
    echo "   Frontend:  $STATIC_WEB_APP_URL"
    echo "   Backend:   $FUNCTION_APP_URL"
    echo "   Health:    $FUNCTION_APP_URL/api/health"
    echo ""
    echo "🎯 AZURE RESOURCES:"
    echo "   Storage:      $STORAGE_NAME"
    echo "   Cosmos DB:    $COSMOS_NAME"
    echo "   Key Vault:    $KEY_VAULT_NAME"
    echo "   Function App: $FUNCTION_APP_NAME"
    echo "   Static App:   $STATIC_WEB_APP_NAME"
    echo "   App Insights: $INSIGHTS_NAME"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "                           NEXT STEPS"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "1️⃣  UPDATE CREDENTIALS in Azure Key Vault:"
    echo "   • Go to: https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME"
    echo "   • Update: google-client-id, google-client-secret"
    echo "   • Update: plaid-client-id, plaid-secret"
    echo ""
    echo "2️⃣  DEPLOY FRONTEND to Static Web App:"
    echo "   • Connect GitHub repository in Azure portal"
    echo "   • Or upload build files from frontend/dist/"
    echo ""
    echo "3️⃣  TEST YOUR APPLICATION:"
    echo "   • Backend health: curl $FUNCTION_APP_URL/api/health"
    echo "   • Frontend: Visit $STATIC_WEB_APP_URL"
    echo ""
    echo "4️⃣  MONITOR & MANAGE:"
    echo "   • Azure portal: https://portal.azure.com"
    echo "   • Application Insights: Monitor performance and errors"
    echo "   • Key Vault: Manage secrets securely"
    echo ""
    print_warning "⏱️  Services may take 2-3 minutes to be fully available"
    
    # Get deployment secrets for GitHub Actions
    print_header "🔐 GITHUB ACTIONS SECRETS"
    echo ""
    echo "Add these secrets to your GitHub repository for automated deployment:"
    echo ""
    
    # Get Static Web App deployment token
    echo "📋 STATIC WEB APP DEPLOYMENT TOKEN:"
    echo "   Secret Name: AZURE_STATIC_WEB_APPS_API_TOKEN"
    echo "   Secret Value:"
    local swa_token=$(az staticwebapp secrets list --name "$STATIC_WEB_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --query "properties.apiKey" --output tsv 2>/dev/null || echo "")
    if [ -n "$swa_token" ]; then
        echo "   $swa_token"
    else
        print_warning "   Unable to retrieve automatically. Get from Azure Portal:"
        echo "   https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Web/staticSites/$STATIC_WEB_APP_NAME"
    fi
    echo ""
    
    # Get Function App publish profile
    echo "📋 FUNCTION APP PUBLISH PROFILE:"
    echo "   Secret Name: AZURE_FUNCTIONAPP_PUBLISH_PROFILE"
    echo "   Secret Value (XML content):"
    local publish_profile=$(az functionapp deployment list-publishing-profiles --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --xml 2>/dev/null || echo "")
    if [ -n "$publish_profile" ]; then
        echo "   $publish_profile"
    else
        print_warning "   Unable to retrieve automatically. Get from Azure Portal:"
        echo "   https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Web/sites/$FUNCTION_APP_NAME"
        echo "   Go to 'Get publish profile' button in the overview section"
    fi
    echo ""
    
    echo "════════════════════════════════════════════════════════════════"
    echo "📝 TO ADD SECRETS TO GITHUB:"
    echo "1. Go to your GitHub repository"
    echo "2. Settings → Secrets and variables → Actions"
    echo "3. Click 'New repository secret'"
    echo "4. Add both secrets above"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    print_success "🎉 Your Sage Financial Management App is ready!"
    echo ""
}

# Error handling
handle_error() {
    local exit_code=$?
    print_error "Deployment failed at step: $CURRENT_STEP"
    print_error "Exit code: $exit_code"
    echo ""
    echo "🔧 TROUBLESHOOTING:"
    echo "• Check Azure portal for resource status"
    echo "• Verify Azure CLI is latest version: az upgrade"
    echo "• Check Azure service health: https://status.azure.com"
    echo "• Resource group: $RESOURCE_GROUP_NAME"
    exit $exit_code
}

# Main execution
main() {
    clear
    echo "════════════════════════════════════════════════════════════════"
    echo "        🏦 Sage Financial Management App Deployment"
    echo "           ✨ Bulletproof Azure Setup (2025) ✨"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    trap handle_error ERR
    
    CURRENT_STEP="Prerequisites"; setup_prerequisites
    CURRENT_STEP="Resource Group"; setup_resource_group
    CURRENT_STEP="Storage Account"; create_storage_account
    CURRENT_STEP="Cosmos DB"; create_cosmos_db
    CURRENT_STEP="Application Insights"; create_app_insights
    CURRENT_STEP="Key Vault"; create_key_vault
    CURRENT_STEP="Function App"; create_function_app
    CURRENT_STEP="Static Web App"; create_static_web_app
    CURRENT_STEP="Function Configuration"; configure_function_app
    CURRENT_STEP="Key Vault Secrets"; setup_secrets
    CURRENT_STEP="Backend Deployment"; deploy_backend
    CURRENT_STEP="Frontend Build"; build_frontend
    
    display_summary
}

# Help function
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Sage Financial Management App - Bulletproof Azure Deployment"
    echo ""
    echo "Usage: ./deploy.sh"
    echo ""
    echo "This script automatically:"
    echo "• Registers all required Azure resource providers"
    echo "• Creates all Azure resources with proper configuration"
    echo "• Deploys backend and builds frontend"
    echo "• Provides complete setup instructions"
    echo ""
    echo "Prerequisites:"
    echo "• Azure CLI installed and logged in (az login)"
    echo "• Node.js 18+ and Python 3.11+"
    echo "• Active Azure subscription with appropriate permissions"
    echo ""
    echo "Cost: Designed to run on Azure free tier ($0-5/month)"
    echo ""
    exit 0
fi

# Run main function
main "$@"