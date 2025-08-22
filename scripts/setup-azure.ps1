# PowerShell script for Azure deployment (Windows users)
# Sage Financial Management App - Azure One-Click Deployment

param(
    [string]$ResourceGroupName = "sage-app-rg",
    [string]$Location = "East US",
    [string]$Environment = "dev"
)

# Color functions
function Write-ColorOutput($Color, $Message) {
    Write-Host $Message -ForegroundColor $Color
}

function Write-Info($Message) {
    Write-ColorOutput Cyan "[INFO] $Message"
}

function Write-Success($Message) {
    Write-ColorOutput Green "[SUCCESS] $Message"
}

function Write-Warning($Message) {
    Write-ColorOutput Yellow "[WARNING] $Message"
}

function Write-Error($Message) {
    Write-ColorOutput Red "[ERROR] $Message"
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Azure CLI
    if (!(Get-Command az -ErrorAction SilentlyContinue)) {
        Write-Error "Azure CLI is not installed. Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    }
    
    # Check Node.js
    if (!(Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Error "Node.js is not installed. Please install it from: https://nodejs.org/"
        exit 1
    }
    
    # Check Python
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python is not installed. Please install it from: https://python.org/"
        exit 1
    }
    
    # Check if logged into Azure
    try {
        az account show | Out-Null
    }
    catch {
        Write-Error "You are not logged into Azure. Please run 'az login' first."
        exit 1
    }
    
    Write-Success "All prerequisites are met!"
}

# Main deployment function
function Start-Deployment {
    Write-Host ""
    Write-Host "=================================================="
    Write-Host "   Sage Financial Management App Deployment      "
    Write-Host "=================================================="
    Write-Host ""
    
    Test-Prerequisites
    
    # Create resource group
    Write-Info "Creating resource group: $ResourceGroupName"
    az group create --name $ResourceGroupName --location $Location
    
    # Deploy infrastructure
    Write-Info "Deploying Azure infrastructure..."
    $deploymentOutput = az deployment group create `
        --resource-group $ResourceGroupName `
        --template-file azure/main.bicep `
        --parameters azure/parameters.json `
        --query "properties.outputs" `
        --output json | ConvertFrom-Json
    
    if ($deploymentOutput) {
        Write-Success "Infrastructure deployed successfully!"
        
        # Extract outputs
        $functionAppName = $deploymentOutput.functionAppName.value
        $staticWebAppName = $deploymentOutput.staticWebAppName.value
        $functionAppUrl = $deploymentOutput.functionAppUrl.value
        $staticWebAppUrl = $deploymentOutput.staticWebAppUrl.value
        
        Write-Info "Function App: $functionAppName"
        Write-Info "Static Web App: $staticWebAppName"
        Write-Info "Function App URL: $functionAppUrl"
        Write-Info "Static Web App URL: $staticWebAppUrl"
        
        # Display completion info
        Write-Host ""
        Write-Success "🎉 Deployment completed successfully!"
        Write-Host ""
        Write-Host "=================================="
        Write-Host "        APPLICATION URLS          "
        Write-Host "=================================="
        Write-Host "Frontend:  $staticWebAppUrl"
        Write-Host "Backend:   $functionAppUrl"
        Write-Host ""
        Write-Host "=================================="
        Write-Host "       NEXT STEPS                 "
        Write-Host "=================================="
        Write-Host "1. Configure your OAuth settings in Google Cloud Console"
        Write-Host "2. Update redirect URIs to use the deployed frontend URL"
        Write-Host "3. Configure Plaid settings for production"
        Write-Host "4. Test the application end-to-end"
        Write-Host ""
    }
    else {
        Write-Error "Infrastructure deployment failed!"
        exit 1
    }
}

# Run deployment
Start-Deployment