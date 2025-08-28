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
PROJECT_NAME="sage"
LOCATION="Central US"
CONSUMPTION_LOCATION="centralus"
ENVIRONMENT="prod"
UNIQUE_SUFFIX="$(date +%s | tail -c 6)4121997"
RESOURCE_GROUP_NAME="${PROJECT_NAME}-rg-${UNIQUE_SUFFIX}"

# Environment array for dev and prod
ENVIRONMENTS=("dev" "prod")

# Variables to store Azure AD credentials for each environment
AZURE_DEV_CLIENT_ID=""
AZURE_DEV_CLIENT_SECRET=""
AZURE_PROD_CLIENT_ID=""
AZURE_PROD_CLIENT_SECRET=""

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

# Function to retry Azure CLI commands with exponential backoff
retry_az_command() {
    local max_attempts=${1:-3}
    local delay=${2:-5}
    local operation_name=${3:-"Azure operation"}
    shift 3  # Remove first 3 arguments, rest are the command
    local cmd=("$@")
    
    local attempt=1
    local exit_code=0
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Attempting $operation_name (attempt $attempt/$max_attempts)..."
        
        if "${cmd[@]}" 2>/dev/null; then
            if [ $attempt -gt 1 ]; then
                print_success "$operation_name succeeded on attempt $attempt"
            fi
            return 0
        else
            exit_code=$?
            if [ $attempt -lt $max_attempts ]; then
                local wait_time=$((delay * attempt))
                print_warning "$operation_name failed (attempt $attempt/$max_attempts). Retrying in ${wait_time}s..."
                sleep $wait_time
            else
                print_error "$operation_name failed after $max_attempts attempts (exit code: $exit_code)"
                print_error "Failed command: ${cmd[*]}"
                return $exit_code
            fi
        fi
        ((attempt++))
    done
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
            retry_az_command 5 10 "Register $provider" az provider register --namespace "$provider" --wait
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
    
    retry_az_command 3 5 "Create resource group $RESOURCE_GROUP_NAME" \
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
    
    retry_az_command 3 10 "Create storage account $STORAGE_NAME" \
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
        
        # Check and create databases if needed
        local databases=("sage-dev-db" "sage-prod-db")
        for database in "${databases[@]}"; do
            if ! az cosmosdb sql database show --account-name "$COSMOS_NAME" --resource-group "$RESOURCE_GROUP_NAME" --name "$database" >/dev/null 2>&1; then
                print_status "Creating missing database: $database"
                retry_az_command 3 10 "Create missing database $database" \
                    az cosmosdb sql database create \
                    --account-name "$COSMOS_NAME" \
                    --resource-group "$RESOURCE_GROUP_NAME" \
                    --name "$database" \
                    --throughput 400 \
                    --output none
            fi
        done
        
        # Check containers for both databases
        local containers=("users" "banks" "transactions" "configuration")
        for database in "${databases[@]}"; do
            for container in "${containers[@]}"; do
                if ! az cosmosdb sql container show --account-name "$COSMOS_NAME" --database-name "$database" --resource-group "$RESOURCE_GROUP_NAME" --name "$container" >/dev/null 2>&1; then
                    print_status "Creating missing container: $container in $database"
                    retry_az_command 3 10 "Create container $container in $database" \
                        az cosmosdb sql container create \
                        --account-name "$COSMOS_NAME" \
                        --resource-group "$RESOURCE_GROUP_NAME" \
                        --database-name "$database" \
                        --name "$container" \
                        --partition-key-path "/userId" \
                        --output none
                fi
            done
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
    if ! retry_az_command 3 15 "Create Cosmos DB with free tier" \
        az cosmosdb create \
        --name "$COSMOS_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --kind GlobalDocumentDB \
        --default-consistency-level Session \
        --enable-free-tier true \
        --enable-automatic-failover false \
        --locations regionName="$LOCATION" failoverPriority=0 isZoneRedundant=false \
        --tags "project=$PROJECT_NAME" \
        --output none; then
        
        print_warning "Free tier not available, creating standard Cosmos DB account..."
        retry_az_command 3 15 "Create standard Cosmos DB account" \
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
    
    # Create dev and prod databases
    print_status "Creating dev database: sage-dev-db"
    retry_az_command 3 10 "Create dev database sage-dev-db" \
        az cosmosdb sql database create \
        --account-name "$COSMOS_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "sage-dev-db" \
        --throughput 400 \
        --output none
        
    print_status "Creating prod database: sage-prod-db"
    retry_az_command 3 10 "Create prod database sage-prod-db" \
        az cosmosdb sql database create \
        --account-name "$COSMOS_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "sage-prod-db" \
        --throughput 400 \
        --output none
    
    # Create containers for both environments
    local containers=("users" "accounts" "transactions" "plaid_tokens")
    local databases=("sage-dev-db" "sage-prod-db")
    
    for database in "${databases[@]}"; do
        for container in "${containers[@]}"; do
            print_status "Creating container: $container in $database"
            retry_az_command 3 10 "Create container $container in $database" \
                az cosmosdb sql container create \
                --account-name "$COSMOS_NAME" \
                --resource-group "$RESOURCE_GROUP_NAME" \
                --database-name "$database" \
                --name "$container" \
                --partition-key-path "/userId" \
                --output none
        done
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
    
    retry_az_command 3 10 "Create Application Insights $INSIGHTS_NAME" \
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
    
    retry_az_command 3 10 "Create Key Vault $KEY_VAULT_NAME" \
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

    # Get the object ID of the currently signed-in user
    local current_user_object_id=$(az ad signed-in-user show --query id -o tsv)
    
    retry_az_command 3 5 "Grant Key Vault Secrets Officer role to current user" \
        az role assignment create \
        --role "Key Vault Secrets Officer" \
        --assignee "$current_user" \
        --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME" \
        --output none
    
    retry_az_command 3 5 "Grant Key Vault Crypto User role to current user" \
        az role assignment create \
        --role "Key Vault Crypto User" \
        --assignee-object-id "$current_user_object_id" \
        --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME" \
        --output none

    # Role for managing cryptographic keys (create, delete)
    retry_az_command 3 5 "Grant Key Vault Crypto Officer role to current user" \
        az role assignment create \
        --role "Key Vault Crypto Officer" \
        --assignee "$current_user" \
        --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME" \
        --output none

    print_success "Key Vault permissions configured!"
    
    # Store function app principal ID for later use (will be set after function app creation)
    FUNCTION_APP_PRINCIPAL_ID=""
}
# Step 6.5: Create or Update Azure AD App Registration
create_azure_ad_app() {
    print_header "STEP 6.5: AZURE AD APP REGISTRATION"
    
    local frontend_url="https://$(echo $STATIC_WEB_APP_NAME | tr '[:upper:]' '[:lower:]').azurestaticapps.net"
    local backend_url="https://${FUNCTION_APP_NAME}.azurewebsites.net"
    
    # Get tenant ID once
    AZURE_AD_TENANT_ID=$(az account show --query tenantId --output tsv)
    
    # Loop through each environment to create/reuse app registrations
    for env in "${ENVIRONMENTS[@]}"; do
        local app_name="sage-${env}-app"
        local APP_REG_ACTION="" # To track if we created or reused the app

        print_status "Processing environment: $env"
        print_status "Checking for existing Azure AD app registration: '$app_name'..."

        # Check if an app with the exact display name already exists
        local client_id=$(az ad app list --display-name "$app_name" --query "[?displayName=='$app_name'].appId" -o tsv 2>/dev/null)

        if [ -n "$client_id" ]; then
            print_warning "Found existing app registration for $env with Client ID: $client_id"
            print_status "Reusing and updating the existing application..."
            APP_REG_ACTION="reused"
        else
            print_status "No existing app found for $env. Creating a new Azure AD app registration..."
            # Create the app registration with basic configuration first
            # Using "AzureADandPersonalMicrosoftAccount" to support both org and personal accounts
            client_id=$(az ad app create \
                --display-name "$app_name" \
                --sign-in-audience "AzureADandPersonalMicrosoftAccount" \
                --query appId \
                --output tsv)
            
            print_success "New app created for $env with Client ID: $client_id"
            print_warning "Waiting 15 seconds for the new app registration to propagate before updating..."
            sleep 15 # Wait a moment for the new app to be fully available for updates
            APP_REG_ACTION="created"
        fi
        
        # Store the client ID for this environment
        if [ "$env" = "dev" ]; then
            AZURE_DEV_CLIENT_ID="$client_id"
        elif [ "$env" = "prod" ]; then
            AZURE_PROD_CLIENT_ID="$client_id"
        fi
        
        # Update the app with web redirect URIs and token configuration
        print_status "Applying latest configuration (redirect URIs, token settings) for $env..."

        # Update Azure AD app configuration using centralized retry logic
        if retry_az_command 3 10 "Update Azure AD app configuration for $env" \
            az ad app update \
            --id "$client_id" \
            --web-redirect-uris "${backend_url}/api/v1/auth/oauth/microsoft/callback" "${frontend_url}/auth/callback" "http://localhost:5173/auth/callback" "http://localhost:8000/api/v1/auth/oauth/microsoft/callback" \
            --enable-access-token-issuance true \
            --enable-id-token-issuance true; then
            print_success "Azure AD app update succeeded for $env. Redirect URIs and token settings applied."
        else
            print_error "Azure AD app update failed for $env after all retry attempts! Some advanced token settings may need manual configuration."
        fi

        # Add Microsoft Graph permissions using centralized retry logic
        if retry_az_command 3 10 "Add Microsoft Graph permissions for $env" \
            az ad app permission add \
            --id "$client_id" \
            --api 00000003-0000-0000-c000-000000000000 \
            --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope 64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0=Scope 14dad69e-099b-42c9-810b-d002981feec1=Scope; then
            print_success "Microsoft Graph permissions added successfully for $env."
        else
            print_error "Failed to add Microsoft Graph permissions for $env after all retry attempts! May need manual configuration."
        fi

        # Create a new client secret with retry logic.
        # This command always generates a *new* secret, which is a good security practice for automated deployments.
        print_status "Resetting client secret for $env to ensure a valid secret is available..."
        local secret_name="sage-${env}-client-secret-$(date +%s)"
        local client_secret=""
        
        # Use a temporary function to capture the output while using retry logic
        get_client_secret() {
            client_secret=$(az ad app credential reset \
                --id "$client_id" \
                --display-name "$secret_name" \
                --years 2 \
                --query password \
                --output tsv)
        }
        
        if retry_az_command 3 10 "Create client secret for $env" get_client_secret; then
            if [ -z "$client_secret" ]; then
                print_error "Client secret creation succeeded but returned empty value for $env"
                print_error "Please try creating the client secret manually in the Azure Portal:"
                print_warning "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Credentials/appId/$client_id"
                exit 1
            fi
        else
            print_error "Failed to create client secret for $env after all retry attempts"
            print_error "Please try creating the client secret manually in the Azure Portal:"
            print_warning "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Credentials/appId/$client_id"
            exit 1
        fi
        
        # Store the client secret for this environment
        if [ "$env" = "dev" ]; then
            AZURE_DEV_CLIENT_SECRET="$client_secret"
        elif [ "$env" = "prod" ]; then
            AZURE_PROD_CLIENT_SECRET="$client_secret"
        fi
        
        print_success "Client secret created/reset successfully for $env."

        # Create service principal for the Azure AD app
        print_status "Creating service principal for $env Azure AD app..."
        local sp_creation_attempt=1
        local sp_max_attempts=3
        local sp_status=1

        while [ $sp_creation_attempt -le $sp_max_attempts ]; do
            if az ad sp create --id "$client_id" --output none 2>/dev/null; then
                print_success "Service principal created successfully for $env."
                sp_status=0
                break
            else
                # Check if service principal already exists
                if az ad sp show --id "$client_id" --output none 2>/dev/null; then
                    print_warning "Service principal already exists for $env. Skipping creation."
                    sp_status=0
                    break
                else
                    print_warning "Service principal creation failed for $env (attempt $sp_creation_attempt/$sp_max_attempts). Retrying in 5 seconds..."
                    sleep 5
                fi
            fi
            
            ((sp_creation_attempt++))
        done

        if [ $sp_status -ne 0 ]; then
            print_error "Failed to create service principal for $env after $sp_max_attempts attempts!"
            print_warning "Manual creation may be required: az ad sp create --id $client_id"
        fi

        print_status "Azure AD Configuration for $env:"
        print_status "  App ID (Client ID): $client_id"
        print_status "  Tenant ID: $AZURE_AD_TENANT_ID"
        print_status "  Sign-in Audience: AzureADandPersonalMicrosoftAccount (supports personal & org accounts)"
        print_status "  Redirect URIs configured for:"
        print_status "    - Production API: ${backend_url}/api/v1/auth/oauth/microsoft/callback"
        print_status "    - Production Web: ${frontend_url}/auth/callback"
        print_status "    - Development API: http://localhost:8000/api/v1/auth/oauth/microsoft/callback"
        print_status "    - Development Web: http://localhost:5173/auth/callback"
        echo ""
        print_status "Azure Portal Link for $env:"
        print_status "  https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/$client_id"
        
        # Show reuse vs creation summary
        echo ""
        if [ "$APP_REG_ACTION" == "reused" ]; then
            print_success "✅ Reused and updated existing Azure AD app registration for $env: $app_name"
        else
            print_success "✅ Created new Azure AD app registration for $env: $app_name"
        fi
        echo ""
    done
    
    # Set the production environment variables for backwards compatibility with the rest of the script
    AZURE_AD_CLIENT_ID="$AZURE_PROD_CLIENT_ID"
    AZURE_AD_CLIENT_SECRET="$AZURE_PROD_CLIENT_SECRET"
    
    print_success "Azure AD app registration completed for all environments!"
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
    retry_az_command 3 15 "Create Function App $FUNCTION_APP_NAME" \
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
    
    # Enable system-assigned managed identity for Key Vault access
    print_status "Enabling managed identity for Function App..."
    retry_az_command 3 10 "Enable managed identity for $FUNCTION_APP_NAME" \
        az functionapp identity assign \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --output none
    
    # Get the managed identity principal ID
    local function_app_principal_id=$(az functionapp identity show \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query principalId \
        --output tsv)
    
    print_success "Managed identity enabled with Principal ID: $function_app_principal_id"
}

# Step 8: Create Static Web App (only if none exists in resource group)
create_static_web_app() {
    print_header "STEP 8: STATIC WEB APP"
    
    # Check if any Static Web App exists in the resource group
    print_status "Checking for existing Static Web Apps in resource group..."
    existing_staticwebapps=$(az staticwebapp list --resource-group "$RESOURCE_GROUP_NAME" --query "[].name" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$existing_staticwebapps" ]; then
        print_status "No existing Static Web App found. Creating new Static Web App: $STATIC_WEB_APP_NAME"
        
        retry_az_command 3 15 "Create Static Web App $STATIC_WEB_APP_NAME" \
            az staticwebapp create \
            --name "$STATIC_WEB_APP_NAME" \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --location "Central US" \
            --sku Free \
            --tags "project=$PROJECT_NAME" \
            --output none
        
        print_success "Static Web App created: $STATIC_WEB_APP_NAME"
    else
        print_warning "Existing Static Web App(s) found in resource group:"
        echo "$existing_staticwebapps" | while read -r app_name; do
            echo "  • $app_name"
        done
        
        # Use the first existing Static Web App
        STATIC_WEB_APP_NAME=$(echo "$existing_staticwebapps" | head -n1)
        print_warning "Using existing Static Web App: $STATIC_WEB_APP_NAME"
        print_warning "Skipping creation of new Static Web App."
    fi
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
    
    # Get Static Web App URL for CORS
    local static_web_app_hostname=$(az staticwebapp show \
        --name "$STATIC_WEB_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query defaultHostname \
        --output tsv 2>/dev/null || echo "localhost")
    local frontend_url="https://${static_web_app_hostname}"
    
    # Configure function app settings with mix of direct values and Key Vault references
    # Infrastructure values: Direct environment variables
    # Sensitive secrets: Key Vault references
    retry_az_command 3 10 "Configure Function App settings" \
        az functionapp config appsettings set \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --settings \
            "COSMOS_DB_ENDPOINT=$cosmos_endpoint" \
            "COSMOS_DB_KEY=$cosmos_key" \
            "COSMOS_DB_NAME=sage-prod-db" \
            "AZURE_CLIENT_ID=@Microsoft.KeyVault(VaultName=${KEY_VAULT_NAME};SecretName=prod-azure-client-id)" \
            "AZURE_CLIENT_SECRET=@Microsoft.KeyVault(VaultName=${KEY_VAULT_NAME};SecretName=prod-azure-client-secret)" \
            "AZURE_TENANT_ID=@Microsoft.KeyVault(VaultName=${KEY_VAULT_NAME};SecretName=prod-azure-tenant-id)" \
            "KEY_VAULT_URL=$key_vault_url" \
            "ENVIRONMENT=$ENVIRONMENT" \
            "APPLICATIONINSIGHTS_CONNECTION_STRING=$insights_connection" \
            "FUNCTIONS_WORKER_RUNTIME=python" \
            "PYTHON_ENABLE_GUNICORN_MULTIPROCESSING=1" \
            "AZURE_REDIRECT_URI=https://${FUNCTION_APP_NAME}.azurewebsites.net/api/v1/auth/oauth/microsoft/callback" \
            "PROJECT_NAME=Sage API" \
            "VERSION=2.0.2" \
            "API_V1_PREFIX=/api/v1" \
            "DEBUG=false" \
            "ALGORITHM=HS256" \
            "ACCESS_TOKEN_EXPIRE_MINUTES=1440" \
            "FRONTEND_URL=$frontend_url" \
            "ALLOWED_HOSTS=${static_web_app_hostname},${FUNCTION_APP_NAME}.azurewebsites.net" \
            "ALLOWED_ORIGINS=$frontend_url,https://${FUNCTION_APP_NAME}.azurewebsites.net,http://localhost:5173,http://localhost:3000" \
            "LOG_LEVEL=INFO" \
            "SESSION_SECRET_KEY=@Microsoft.KeyVault(VaultName=${KEY_VAULT_NAME};SecretName=session-secret-key)" \
        --output none
    
    print_status "Configuring Function App CORS settings..."
    
    # Configure CORS directly in Function App (separate from environment variables)
    retry_az_command 2 3 "Add CORS origin $frontend_url" \
        az functionapp cors add \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --allowed-origins "$frontend_url" \
        --output none || true
        
    retry_az_command 2 3 "Add CORS origin https://${FUNCTION_APP_NAME}.azurewebsites.net" \
        az functionapp cors add \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --allowed-origins "https://${FUNCTION_APP_NAME}.azurewebsites.net" \
        --output none || true
        
    retry_az_command 2 3 "Add CORS origin http://localhost:5173" \
        az functionapp cors add \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --allowed-origins "http://localhost:5173" \
        --output none || true
        
    retry_az_command 2 3 "Add CORS origin http://localhost:3000" \
        az functionapp cors add \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --allowed-origins "http://localhost:3000" \
        --output none || true
    
    # Enable credentials for CORS (needed for authentication)
    retry_az_command 2 3 "Enable CORS credentials" \
        az functionapp cors credentials \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --enable true \
        --output none || true
    
    print_success "Function App configured with environment variables and CORS settings!"
    
    # Grant Function App managed identity access to Key Vault
    print_status "Granting Function App access to Key Vault..."
    local function_app_principal_id=$(az functionapp identity show \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query principalId \
        --output tsv)
    
    if [ -n "$function_app_principal_id" ]; then
        # Grant Key Vault roles (required for Function App Key Vault references)
        print_status "Granting Key Vault Secrets User role..."
        retry_az_command 3 5 "Grant Key Vault Secrets User role" \
            az role assignment create \
            --role "Key Vault Secrets User" \
            --assignee "$function_app_principal_id" \
            --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME" \
            --output none
            
        print_status "Granting Key Vault Reader role..."
        retry_az_command 3 5 "Grant Key Vault Reader role" \
            az role assignment create \
            --role "Key Vault Reader" \
            --assignee "$function_app_principal_id" \
            --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME" \
            --output none
            
        print_status "Granting Key Vault Crypto User role..."
        retry_az_command 3 5 "Grant Key Vault Crypto User role" \
            az role assignment create \
            --role "Key Vault Crypto User" \
            --assignee "$function_app_principal_id" \
            --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME" \
            --output none
        
        print_success "Function App granted Key Vault access with required roles!"
    else
        print_warning "Could not retrieve Function App principal ID. Key Vault access may need manual configuration."
    fi
}

# Step 10: Setup secrets in Key Vault
setup_secrets() {
    print_header "STEP 10: KEY VAULT SECRETS"
    
    print_status "Setting up secrets in Key Vault..."
    print_warning "Waiting for Key Vault permissions to propagate..."
    sleep 15
    
    
    # Create environment-specific secrets (both dev and prod)
    print_status "Creating dev and prod environment secrets..."
    
    # Dev environment secrets (only actual secrets, not infrastructure config)
    local dev_secrets=(
        "dev-azure-client-id:$AZURE_DEV_CLIENT_ID"
        "dev-azure-client-secret:$AZURE_DEV_CLIENT_SECRET"
        "dev-azure-tenant-id:$AZURE_AD_TENANT_ID"
    )
    
    # Prod environment secrets (only actual secrets, not infrastructure config)
    local prod_secrets=(
        "prod-azure-client-id:$AZURE_PROD_CLIENT_ID"
        "prod-azure-client-secret:$AZURE_PROD_CLIENT_SECRET"
        "prod-azure-tenant-id:$AZURE_AD_TENANT_ID"
        "session-secret-key:$(openssl rand -base64 32)"
    )

    # Combine all secrets
    local secrets=("${dev_secrets[@]}" "${prod_secrets[@]}")
    
    for secret_pair in "${secrets[@]}"; do
        local secret_name=$(echo "$secret_pair" | cut -d: -f1)
        local secret_value=$(echo "$secret_pair" | cut -d: -f2-)

        if retry_az_command 3 5 "Set secret $secret_name" \
            az keyvault secret set \
            --vault-name "$KEY_VAULT_NAME" \
            --name "$secret_name" \
            --value "$secret_value" \
            --output none; then
            print_status "Set secret: $secret_name"
        else
            print_error "Failed to set secret: $secret_name after all retry attempts"
        fi
    done

    print_status "Creating cryptographic key for encryption and JWT signing..."

    # Create single key for both encryption and JWT signing operations
    if retry_az_command 3 10 "Create cryptographic key secrets-encryption-key" \
        az keyvault key create \
        --vault-name "$KEY_VAULT_NAME" \
        --name "secrets-encryption-key" \
        --kty RSA \
        --size 2048 \
        --ops encrypt decrypt sign verify \
        --protection software \
        --output none; then
        print_success "Successfully created cryptographic key: 'secrets-encryption-key'"
    else
        print_warning "Key creation failed, attempting to update existing key operations..."
        # Update existing key to include sign/verify operations
        if retry_az_command 3 5 "Update key operations for secrets-encryption-key" \
            az keyvault key set-attributes \
            --vault-name "$KEY_VAULT_NAME" \
            --name "secrets-encryption-key" \
            --ops encrypt decrypt sign verify \
            --output none; then
            print_success "Successfully updated key operations for 'secrets-encryption-key'"
        else
            print_error "Failed to create or update cryptographic key. Manual intervention may be required."
        fi
    fi
    
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

force_config_refresh() {
    print_header "STEP 11.5: FORCING CONFIGURATION REFRESH"
    print_warning "Forcing a platform-level refresh of all settings by updating a dummy variable..."
    print_warning "This is the definitive way to ensure new Key Vault secret versions are loaded."
    
    retry_az_command 3 5 "Force configuration refresh" \
        az functionapp config appsettings set \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --settings "LAST_CONFIG_REFRESH_TIMESTAMP=$(date +%s)" \
        --output none
        
    print_success "Configuration refresh triggered. It may take 2-3 minutes for the app to be ready."
}

# Step 12: Build and Deploy frontend to Static Web App (Production)
deploy_frontend() {
    print_header "STEP 12: FRONTEND BUILD & PRODUCTION DEPLOYMENT"
    
    print_status "Building and deploying React frontend to PRODUCTION..."
    
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
VITE_API_BASE_URL=${function_app_url}/api/v1
VITE_APP_ENV=production
VITE_GOOGLE_CLIENT_ID=configure-me
EOF
    
    # Build application
    print_status "Building application..."
    npm run build --silent
    
    print_success "Frontend built successfully!"
    
    # Deploy to Azure Static Web App PRODUCTION using SWA CLI
    print_status "Deploying to Azure Static Web App PRODUCTION environment..."
    
    # Get deployment token
    local deployment_token=$(az staticwebapp secrets list \
        --name "$STATIC_WEB_APP_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query "properties.apiKey" \
        --output tsv 2>/dev/null)
    
    if [ -z "$deployment_token" ]; then
        print_error "Could not retrieve deployment token. Please deploy manually."
        print_warning "Manual deployment steps:"
        print_warning "1. Get deployment token from Azure Portal"
        print_warning "2. Run: npx @azure/static-web-apps-cli deploy --deployment-token <token> --app-location ./dist --env production"
    else
        # Check if SWA CLI is installed, if not install it
        if ! command_exists swa; then
            print_status "Installing Azure Static Web Apps CLI..."
            npm install -g @azure/static-web-apps-cli
        fi
        
        # Deploy using SWA CLI with PRODUCTION environment
        print_status "Deploying build files to Static Web App PRODUCTION..."
        local retry_count=0
        local max_retries=2
        
        while [ $retry_count -lt $max_retries ]; do
            if npx @azure/static-web-apps-cli deploy \
                --app-location ./dist \
                --deployment-token "$deployment_token" \
                --env production \
                --verbose; then
                print_success "Frontend deployed successfully to PRODUCTION environment!"
                break
            else
                ((retry_count++))
                if [ $retry_count -lt $max_retries ]; then
                    print_warning "Deployment retry $retry_count/$max_retries"
                    sleep 15
                else
                    print_error "Frontend deployment failed after $max_retries attempts"
                    print_warning "You can deploy manually using:"
                    print_warning "npx @azure/static-web-apps-cli deploy --app-location ./dist --deployment-token $deployment_token --env production"
                fi
            fi
        done
    fi
    
    cd ..
    
    # Store URLs for final output
    FUNCTION_APP_URL="$function_app_url"
    STATIC_WEB_APP_URL="$static_web_app_url"
    
    print_success "Frontend production deployment completed!"
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
    echo "   Health:    $FUNCTION_APP_URL/health"
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
    echo "1️⃣  MICROSOFT ENTRA ID LOGIN:"
    echo "   • Microsoft Entra ID is configured to support BOTH:"
    echo "     - Personal Microsoft accounts (outlook.com, hotmail.com, live.com)"
    echo "     - Organizational Azure AD accounts"
    echo "   • Login at: $STATIC_WEB_APP_URL"
    echo ""
    echo "4️⃣  DEPLOY FRONTEND to Static Web App:"
    echo "   • Connect GitHub repository in Azure portal"
    echo "   • Or upload build files from frontend/dist/"
    echo ""
    echo "5️⃣  RESTART FUNCTION APP (Important for Key Vault references):"
    echo "   • az functionapp restart --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP_NAME"
    echo "   • Wait 2-3 minutes after restart for Key Vault references to resolve"
    echo ""
    echo "6️⃣  TEST YOUR APPLICATION:"
    echo "   • Backend health: curl $FUNCTION_APP_URL/health"
    echo "   • Frontend: Visit $STATIC_WEB_APP_URL"
    echo "   • Plaid status: GET $FUNCTION_APP_URL/api/v1/plaid/configuration/status"
    echo ""
    echo "7️⃣  MONITOR & MANAGE:"
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
        print_warning "   Unable to retrieve automatically for the app: "$STATIC_WEB_APP_NAME" in the resource group: "$RESOURCE_GROUP_NAME". Get from Azure Portal:"
        echo "   https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Web/staticSites/$STATIC_WEB_APP_NAME"
    fi
    echo ""
    echo ""
    
    # Get Function App publish profile with retry logic and multiple methods
    echo "📋 FUNCTION APP PUBLISH PROFILE:"
    echo "   Secret Name: AZURE_FUNCTIONAPP_PUBLISH_PROFILE"
    echo "   Secret Value (XML content):"
    
    local publish_profile=""
    local retry_count=0
    local max_retries=3
    
    # Method 1: Standard list-publishing-profiles command with retries
    while [ $retry_count -lt $max_retries ] && [ -z "$publish_profile" ]; do
        print_status "Attempting to retrieve publish profile (attempt $((retry_count + 1))/$max_retries)..."
        publish_profile=$(az functionapp deployment list-publishing-profiles \
            --name "$FUNCTION_APP_NAME" \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --xml 2>/dev/null || echo "")
        
        if [ -n "$publish_profile" ]; then
            print_success "Successfully retrieved publish profile!"
            break
        fi
        
        ((retry_count++))
        if [ $retry_count -lt $max_retries ]; then
            print_warning "Retry in 10 seconds..."
            sleep 10
        fi
    done
    
    # Method 2: Alternative approach using webapp deployment if function app method fails
    if [ -z "$publish_profile" ]; then
        print_status "Trying alternative method using webapp deployment..."
        publish_profile=$(az webapp deployment list-publishing-profiles \
            --name "$FUNCTION_APP_NAME" \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --xml 2>/dev/null || echo "")
    fi
    
    # Method 3: Force refresh the function app and try again
    if [ -z "$publish_profile" ]; then
        print_status "Forcing function app sync and retrying..."
        retry_az_command 2 5 "Sync Function App" \
            az functionapp sync --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP_NAME" --output none || true
        sleep 5
        publish_profile=$(az functionapp deployment list-publishing-profiles \
            --name "$FUNCTION_APP_NAME" \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --xml 2>/dev/null || echo "")
    fi
    
    if [ -n "$publish_profile" ]; then
        echo "   $publish_profile"
        print_success "✅ Publish profile retrieved successfully!"
    else
        print_error "❌ Unable to retrieve publish profile automatically after all attempts."
        print_warning "Manual steps to get publish profile:"
        print_warning "1. Go to Azure Portal: https://portal.azure.com"
        print_warning "2. Navigate to: Resource Groups → $RESOURCE_GROUP_NAME → $FUNCTION_APP_NAME"
        print_warning "3. Click 'Get publish profile' button in the overview section"
        print_warning "4. Copy the entire XML content as the secret value"
        echo ""
        print_warning "Or try this Azure CLI command manually:"
        echo "   az functionapp deployment list-publishing-profiles --name \"$FUNCTION_APP_NAME\" --resource-group \"$RESOURCE_GROUP_NAME\" --xml"
    fi
    echo ""

    # Get front end app api url
    echo "📋 FRONTEND APP BASE API URL:"
    echo "   Secret Name: AZURE_FUNCTION_APP_URL"
    echo "   Secret Value:"
    echo "   $FUNCTION_APP_URL"
    
    echo "════════════════════════════════════════════════════════════════"
    echo "📝 TO ADD SECRETS TO GITHUB:"
    echo "1. Go to your GitHub repository"
    echo "2. Settings → Secrets and variables → Actions"
    echo "3. Click 'New repository secret'"
    echo "4. Add these 3 secrets:"
    echo "   - AZURE_STATIC_WEB_APPS_API_TOKEN (from above)"
    echo "   - AZURE_FUNCTIONAPP_PUBLISH_PROFILE (from above)"
    echo "   - AZURE_FUNCTION_APP_URL: $FUNCTION_APP_URL"
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
    echo "        🏦 Sage - Azure setup v1.0"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    trap handle_error ERR
    
    CURRENT_STEP="Prerequisites"; setup_prerequisites
    CURRENT_STEP="Resource Group"; setup_resource_group
    CURRENT_STEP="Storage Account"; create_storage_account
    CURRENT_STEP="Cosmos DB"; create_cosmos_db
    CURRENT_STEP="Application Insights"; create_app_insights
    CURRENT_STEP="Key Vault"; create_key_vault
    CURRENT_STEP="Azure AD App Registration"; create_azure_ad_app
    CURRENT_STEP="Function App"; create_function_app
    CURRENT_STEP="Static Web App"; create_static_web_app
    CURRENT_STEP="Function Configuration"; configure_function_app
    CURRENT_STEP="Key Vault Secrets"; setup_secrets
    CURRENT_STEP="Backend Deployment"; deploy_backend
    CURRENT_STEP="Force Config Refresh"; force_config_refresh
    CURRENT_STEP="Frontend Deployment"; deploy_frontend
    
    
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