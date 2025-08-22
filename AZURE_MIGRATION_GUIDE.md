# Azure Migration Guide

## 🎯 Complete Migration to Azure Ecosystem

This guide walks you through the complete migration from Google Cloud Platform to Microsoft Azure for the Sage Financial Management Application.

## 📋 Migration Overview

### What's Changed

| Component | Before (GCP) | After (Azure) |
|-----------|-------------|---------------|
| **Backend** | FastAPI on Cloud Run | Azure Functions (Python) |
| **Database** | Firebase Firestore | Azure Cosmos DB |
| **Frontend Hosting** | Firebase Hosting | Azure Static Web Apps |
| **Secrets Management** | Google Secret Manager | Azure Key Vault |
| **Authentication** | Firebase Auth + Google OAuth | Google OAuth + JWT |
| **Monitoring** | Google Cloud Logging | Application Insights |
| **Infrastructure** | Manual/Terraform | Azure Bicep |
| **Deployment** | Manual deployment | One-click automated |

### Why Azure?

1. **Cost Optimization**: Azure's free tier is more generous
2. **Serverless Excellence**: Azure Functions provide better Python support
3. **Integrated Ecosystem**: Better integration between services
4. **Enterprise Ready**: Superior enterprise features and compliance
5. **Global Reach**: More regions and edge locations

## 🚀 Quick Start (Recommended)

### Option 1: One-Click Deployment

```bash
# Clone the repository
git clone <your-repository-url>
cd personal-wealth-management

# Login to Azure
az login

# Run the automated deployment
./deploy.sh
```

That's it! The script will:
- Create all Azure resources
- Deploy the backend and frontend
- Configure secrets management
- Provide you with live URLs

### Option 2: Step-by-Step Deployment

If you prefer to understand each step:

#### 1. Prerequisites Setup

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Login to Azure
az login
```

#### 2. Infrastructure Deployment

```bash
# Create resource group
az group create --name sage-app-rg --location "East US"

# Deploy infrastructure
az deployment group create \
  --resource-group sage-app-rg \
  --template-file azure/main.bicep \
  --parameters azure/parameters.json
```

#### 3. Backend Deployment

```bash
cd server-azure

# Install dependencies
pip install -r requirements.txt

# Deploy to Azure Functions
func azure functionapp publish <function-app-name> --python
```

#### 4. Frontend Deployment

```bash
cd frontend

# Install dependencies
npm install

# Build the application
npm run build

# Deploy to Azure Static Web Apps (via Azure portal or GitHub integration)
```

## 🔧 Configuration

### Required Secrets

Configure these secrets in Azure Key Vault:

```bash
# JWT Secret (auto-generated if not provided)
az keyvault secret set --vault-name <vault-name> --name "jwt-secret" --value "<your-secret>"

# Google OAuth Credentials
az keyvault secret set --vault-name <vault-name> --name "google-client-id" --value "<your-client-id>"
az keyvault secret set --vault-name <vault-name> --name "google-client-secret" --value "<your-client-secret>"

# Plaid API Credentials
az keyvault secret set --vault-name <vault-name> --name "plaid-client-id" --value "<your-plaid-client-id>"
az keyvault secret set --vault-name <vault-name> --name "plaid-secret" --value "<your-plaid-secret>"
```

### Environment Variables

The application will automatically configure environment variables, but you can customize:

```bash
# Azure Functions Configuration
COSMOS_DB_ENDPOINT=<automatically-set>
COSMOS_DB_KEY=<automatically-set>
KEY_VAULT_URL=<automatically-set>
ENVIRONMENT=production

# Frontend Configuration (Azure Static Web Apps)
VITE_API_BASE_URL=<automatically-set>
VITE_GOOGLE_CLIENT_ID=<your-google-client-id>
```

## 🔄 Migration from GCP

### Data Migration

If you have existing data in Firebase Firestore:

1. **Export Firestore Data**
   ```bash
   gcloud firestore export gs://<your-bucket>/firestore-export
   ```

2. **Convert to Cosmos DB Format**
   ```python
   # Use the migration script (to be created)
   python scripts/migrate-firestore-to-cosmosdb.py
   ```

3. **Import to Cosmos DB**
   ```bash
   # Use Azure Data Factory or custom import script
   ```

### User Migration

- Users will need to re-authenticate with Google OAuth
- Plaid connections will need to be re-established
- Historical data can be migrated using the data migration process

## 📊 Service Mapping

### Database Schema Migration

Firebase Firestore collections map to Cosmos DB containers:

| Firestore Collection | Cosmos DB Container | Partition Key |
|----------------------|-------------------|---------------|
| `users` | `users` | `/userId` |
| `accounts` | `accounts` | `/userId` |
| `transactions` | `transactions` | `/userId` |
| `plaid_tokens` | `plaid_tokens` | `/userId` |

### API Endpoint Migration

| GCP Endpoint | Azure Endpoint | Notes |
|-------------|----------------|-------|
| `/auth/oauth/google` | `/auth/google/login` | Simplified flow |
| `/plaid/*` | `/plaid/*` | Same structure |
| `/users/*` | `/users/*` | Same structure |
| `/health` | `/health` | Enhanced with Azure metrics |

## 🔍 Testing the Migration

### 1. Health Check

```bash
curl https://<function-app-name>.azurewebsites.net/api/health
```

### 2. Authentication Test

```bash
# Test Google OAuth flow
# Visit: https://<static-web-app-name>.azurestaticapps.net
```

### 3. Plaid Integration Test

```bash
# After authentication, test Plaid link token creation
curl -X POST https://<function-app-name>.azurewebsites.net/api/plaid/create_link_token \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json"
```

## 📈 Monitoring and Maintenance

### Azure Application Insights

- **Automatic Setup**: Configured during deployment
- **Custom Dashboards**: Available in Azure portal
- **Alerts**: Set up proactive monitoring

### Cost Monitoring

- **Azure Cost Management**: Track spending
- **Budget Alerts**: Set spending limits
- **Resource Tagging**: Organize costs by feature

### Backup and Disaster Recovery

- **Cosmos DB Backup**: Automatic continuous backup
- **Function App Backup**: Source code in GitHub
- **Key Vault Backup**: Automatic backup enabled

## ⚠️ Known Issues and Solutions

### 1. Cold Start Latency

**Issue**: Azure Functions may have cold start delays
**Solution**: Use Premium plan for production or implement warming strategies

### 2. Cosmos DB Request Units

**Issue**: May exceed free tier RU limits with high usage
**Solution**: Monitor usage and upgrade to provisioned throughput if needed

### 3. CORS Configuration

**Issue**: Frontend may have CORS issues during development
**Solution**: Update CORS settings in Function App configuration

## 🎓 Best Practices

### Security

1. **Use Managed Identity**: Enable system-assigned managed identity
2. **Key Vault Integration**: Store all secrets in Key Vault
3. **Network Security**: Configure private endpoints for production
4. **Monitoring**: Enable security monitoring and alerts

### Performance

1. **Partition Key Design**: Optimize Cosmos DB partition keys
2. **Function Optimization**: Keep functions lightweight
3. **Caching**: Implement client-side caching with React Query
4. **CDN Usage**: Leverage Azure CDN for static assets

### Cost Optimization

1. **Resource Tagging**: Tag all resources for cost tracking
2. **Monitoring**: Set up cost alerts and budgets
3. **Scaling**: Use consumption plans for variable workloads
4. **Cleanup**: Remove unused resources regularly

## 🆘 Troubleshooting

### Common Issues

1. **Deployment Fails**
   - Check Azure CLI login: `az account show`
   - Verify subscription permissions
   - Check resource naming conflicts

2. **Function App Not Starting**
   - Check Python version compatibility
   - Verify requirements.txt
   - Check Application Insights logs

3. **Database Connection Issues**
   - Verify Cosmos DB firewall settings
   - Check managed identity permissions
   - Validate connection strings

4. **Authentication Problems**
   - Verify Google OAuth configuration
   - Check redirect URIs
   - Validate JWT secret configuration

### Support Resources

- **Azure Documentation**: [docs.microsoft.com](https://docs.microsoft.com/azure)
- **Azure Support**: Available through Azure portal
- **Community**: Stack Overflow with `azure` tag
- **GitHub Issues**: Report bugs in this repository

## 🎉 Success Metrics

After successful migration, you should see:

- ✅ Application running on Azure Functions
- ✅ Data stored in Azure Cosmos DB
- ✅ Frontend hosted on Azure Static Web Apps
- ✅ Secrets managed in Azure Key Vault
- ✅ Monitoring in Application Insights
- ✅ Costs within Azure free tier limits

## 📞 Getting Help

If you encounter issues during migration:

1. Check the troubleshooting section above
2. Review Azure Application Insights logs
3. Use `func azure functionapp logstream` for real-time debugging
4. Create an issue in this repository with detailed error logs

---

**Congratulations!** You've successfully migrated to Azure and gained access to enterprise-grade serverless infrastructure with better cost optimization and global scalability.