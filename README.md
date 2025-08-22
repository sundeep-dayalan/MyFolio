# Sage - Financial Management Application

## 🌟 Overview

Sage is a comprehensive financial management application that integrates with Plaid to provide real-time financial data analysis, transaction tracking, and portfolio management. The application features a modern React frontend with an Azure Functions backend, all designed for production deployment on Microsoft Azure.

## 🚀 One-Click Azure Deployment

**Get started in minutes with our automated Azure deployment:**

```bash
git clone https://github.com/your-username/personal-wealth-management.git
cd personal-wealth-management
./deploy.sh
```

This will automatically provision all Azure resources and deploy your application!

## 🏗️ Architecture

### System Architecture

```
Frontend (React + TypeScript)
├── Vite Build System
├── React Query for State Management
├── React Router for Navigation
├── Tailwind CSS for Styling
└── Azure Static Web Apps Hosting

Backend (Azure Functions + Python)
├── Serverless Architecture
├── JWT Authentication
├── Azure Cosmos DB Database
├── Azure Functions Runtime
└── Plaid Integration

Azure Services
├── Azure Functions (Serverless Backend)
├── Azure Cosmos DB (NoSQL Database)
├── Azure Static Web Apps (Frontend Hosting)
├── Azure Key Vault (Secrets Management)
└── Application Insights (Monitoring)

External Services
├── Plaid API (Financial Data)
└── Google OAuth (Authentication)
```

### Project Structure

```
personal-wealth-management/
├── server/                       # FastAPI backend (deployable to Azure Functions)
│   ├── app/                      # Main application package
│   │   ├── config.py            # Azure configuration and Key Vault
│   │   ├── database.py          # Azure Cosmos DB connection
│   │   ├── services/            # Business logic layer
│   │   │   ├── auth_service.py  # Authentication with Azure AD
│   │   │   └── plaid_service.py # Plaid integration
│   │   └── utils/               # Security and utility functions
│   ├── function_app.py          # Azure Functions entry point
│   ├── requirements.txt         # Python dependencies
│   ├── host.json               # Function app configuration
│   └── local.settings.json     # Local development settings
├── frontend/                    # React frontend for Azure Static Web Apps
│   ├── src/
│   │   ├── components/         # Reusable React components
│   │   ├── pages/              # Page components
│   │   ├── services/           # Azure-compatible API services
│   │   ├── hooks/              # Custom React hooks
│   │   └── types/              # TypeScript definitions
│   ├── staticwebapp.config.json # Azure Static Web Apps config
│   └── package.json            # Dependencies and build scripts
├── azure/                       # Infrastructure as Code
│   ├── main.bicep              # Azure resource definitions
│   └── parameters.json         # Deployment parameters
├── scripts/                     # Deployment and setup scripts
│   ├── local-dev-setup.sh      # Local development setup
│   └── setup-azure.ps1         # PowerShell deployment script
└── deploy.sh                   # One-click deployment script
```

## 🚀 Features

### Financial Management

- **Account Integration**: Connect multiple bank accounts through Plaid
- **Real-time Balances**: View current account balances and positions
- **Transaction Tracking**: Monitor and categorize financial transactions
- **Portfolio Overview**: Comprehensive view of financial assets
- **Security**: End-to-end encrypted token storage

### User Experience

- **Google OAuth**: Seamless authentication with Google accounts
- **Responsive Design**: Mobile-first responsive interface
- **Real-time Updates**: Live data synchronization
- **Intuitive Navigation**: Clean, modern user interface

### Technical Features

- **Production Ready**: Optimized for production deployment
- **Type Safety**: Full TypeScript implementation
- **Error Handling**: Comprehensive error management
- **Monitoring**: Built-in logging and health checks
- **Scalability**: Designed for horizontal scaling

## 🛠️ Technology Stack

### Frontend

- **React 19.1.1**: Modern React with hooks and context
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and development server
- **React Router 7.7.1**: Client-side routing
- **React Query**: Server state management
- **Tailwind CSS**: Utility-first CSS framework
- **React Plaid Link**: Official Plaid React component

### Backend

- **Azure Functions**: Serverless Python runtime
- **Python 3.11**: Optimized for Azure Functions
- **Pydantic**: Data validation and settings management
- **Azure Cosmos DB SDK**: NoSQL document database
- **Azure Key Vault SDK**: Secure secrets management
- **Plaid Python SDK**: Financial data integration
- **JWT**: Secure token-based authentication

### Azure Infrastructure

- **Azure Functions**: Serverless backend hosting
- **Azure Cosmos DB**: Serverless NoSQL database
- **Azure Static Web Apps**: Frontend hosting with CDN
- **Azure Key Vault**: Centralized secrets management
- **Application Insights**: Monitoring and analytics
- **Azure Bicep**: Infrastructure as Code

## 🔧 Quick Start

### One-Click Deployment

Deploy to Azure in under 5 minutes:

```bash
# Clone the repository
git clone <repository-url>
cd personal-wealth-management

# Run the deployment script
./deploy.sh
```

The script will:
- Create Azure resource group
- Deploy all infrastructure (Functions, Cosmos DB, Static Web Apps, Key Vault)
- Configure secrets management
- Deploy both frontend and backend
- Provide you with live URLs

### Local Development Setup

For local development:

```bash
# Setup local development environment
./scripts/local-dev-setup.sh

# Start the backend (Azure Functions)
cd server
source venv/bin/activate
func start

# Start the frontend (in another terminal)
cd frontend
npm run dev
```

### Prerequisites

- **Azure Account**: Free account works perfectly
- **Python 3.11+**: For Azure Functions runtime
- **Node.js 18+**: For React frontend
- **Azure CLI**: For deployment and management
- **Plaid Developer Account**: For financial data integration
- **Google Cloud Console**: For OAuth credentials

## 🌐 Deployment Options

### Option 1: Automated Deployment (Recommended)

The fastest way to deploy:

```bash
./deploy.sh
```

This handles everything automatically including:
- Azure resource provisioning
- Infrastructure configuration
- Secret management setup
- Application deployment

### Option 2: Manual Azure Deployment

If you prefer manual control:

```bash
# 1. Deploy infrastructure
az group create --name sage-app-rg --location "East US"
az deployment group create --resource-group sage-app-rg --template-file azure/main.bicep

# 2. Deploy backend
cd server
func azure functionapp publish <function-app-name>

# 3. Deploy frontend
cd frontend
npm run build
# Deploy via Azure portal or Azure CLI
```

### Option 3: Infrastructure as Code Only

Deploy just the infrastructure:

```bash
az deployment group create \
  --resource-group sage-app-rg \
  --template-file azure/main.bicep \
  --parameters azure/parameters.json
```

### Environment Configuration

The application uses Azure Key Vault for secure configuration management:

#### Required Secrets in Azure Key Vault:

- `jwt-secret`: JWT token signing key
- `google-client-id`: Google OAuth client ID
- `google-client-secret`: Google OAuth client secret
- `plaid-client-id`: Plaid API client ID
- `plaid-secret`: Plaid API secret key

#### Environment Variables:

```bash
# Azure Functions Configuration
COSMOS_DB_ENDPOINT=<your-cosmos-db-endpoint>
COSMOS_DB_KEY=<managed-by-azure>
KEY_VAULT_URL=<your-key-vault-url>
ENVIRONMENT=production

# Frontend Configuration (Azure Static Web Apps)
VITE_API_BASE_URL=<your-function-app-url>/api
VITE_GOOGLE_CLIENT_ID=<your-google-client-id>
```

## 🔐 Security

### Azure-Native Security

- **Azure Key Vault**: Centralized secrets management with HSM-backed keys
- **Azure Managed Identity**: Passwordless authentication between services
- **Azure Cosmos DB**: Built-in encryption at rest and in transit
- **Azure Functions**: Isolated execution environment with auto-scaling

### Authentication & Authorization

- **Google OAuth 2.0**: Secure user authentication flow
- **JWT Tokens**: Stateless authentication with configurable expiration
- **Token Encryption**: Plaid tokens encrypted using Azure Key Vault
- **Secure Storage**: User data isolated by partition keys in Cosmos DB

### API Security

- **CORS Configuration**: Properly configured for Azure Static Web Apps
- **Input Validation**: Comprehensive request validation with Pydantic
- **Error Handling**: Secure error responses without sensitive data exposure
- **Azure Functions Security**: Built-in DDoS protection and traffic filtering

### Data Protection

- **Encryption at Rest**: Azure Cosmos DB automatic encryption
- **HTTPS Only**: TLS 1.2+ enforced across all Azure services
- **Azure Key Vault**: Hardware-backed secret storage
- **Network Security**: Private endpoints and service-to-service authentication

## 📊 API Documentation

### Azure Functions Endpoints

Base URL: `https://<your-function-app>.azurewebsites.net/api`

### Authentication Endpoints

- `POST /auth/google/login` - Google OAuth login with authorization code
- `POST /auth/refresh` - Refresh JWT token
- `GET /health` - Application health check

### User Management

- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update user profile
- `DELETE /users/me` - Delete user account and all data

### Plaid Integration

- `POST /plaid/create_link_token` - Create Plaid Link token
- `POST /plaid/exchange_public_token` - Exchange public token for access token
- `GET /plaid/accounts` - Get user's financial accounts
- `GET /plaid/transactions` - Retrieve transaction history

### Request Authentication

All protected endpoints require a Bearer token:

```javascript
headers: {
  'Authorization': 'Bearer <jwt-token>',
  'Content-Type': 'application/json'
}
```

## 🧪 Testing

### Local Testing

Test the Azure Functions locally:

```bash
cd server
source venv/bin/activate
func start
```

Test the React frontend:

```bash
cd frontend
npm run dev
```

### Production Testing

Test deployed Azure Functions:

```bash
# Health check
curl https://<your-function-app>.azurewebsites.net/api/health

# Test authentication (replace with actual Google auth code)
curl -X POST https://<your-function-app>.azurewebsites.net/api/auth/google/login \
  -H "Content-Type: application/json" \
  -d '{"code": "your-google-auth-code", "redirect_uri": "your-redirect-uri"}'
```

### Integration Testing

The application includes comprehensive testing for:

- Azure Functions HTTP triggers
- Azure Cosmos DB operations
- Plaid API integration
- Google OAuth authentication flow
- Azure Key Vault secret management

## 📈 Monitoring & Logging

### Azure Application Insights

- **Real-time Monitoring**: Automatic performance tracking
- **Custom Telemetry**: Business metrics and user analytics
- **Error Tracking**: Automatic exception capture and alerting
- **Performance Monitoring**: Response times and dependency tracking

### Azure Monitor Integration

- **Log Analytics**: Centralized log aggregation and querying
- **Alerts**: Proactive monitoring with email/SMS notifications
- **Dashboards**: Custom visualizations and KPI tracking
- **Health Checks**: Built-in availability monitoring

### Logging Strategy

- **Structured Logging**: JSON-formatted logs for easy parsing
- **Request Correlation**: Trace requests across Azure services
- **Security Logging**: Authentication and authorization events
- **Performance Logging**: Function execution times and costs

## 🔮 Production Optimization

### Azure-Native Performance

- **Serverless Auto-scaling**: Azure Functions automatically scale based on demand
- **Global CDN**: Azure Static Web Apps with worldwide edge locations
- **Cosmos DB Optimization**: Partition key design for optimal performance
- **Connection Pooling**: Azure SDK automatic connection management

### Cost Optimization

- **Consumption-based Pricing**: Pay only for actual usage
- **Free Tier Eligible**: Most services fit within Azure free tier limits
- **Automatic Scaling**: Scale to zero when not in use
- **Resource Tagging**: Track and optimize costs by feature

### Scalability Features

- **Serverless Architecture**: Infinite horizontal scaling capability
- **Database Partitioning**: Cosmos DB auto-scaling and partitioning
- **Global Distribution**: Multi-region deployment ready
- **Traffic Management**: Azure Front Door for global load balancing

## 📚 Development Guidelines

### Azure-Specific Best Practices

- **Managed Identity**: Use Azure Managed Identity for service-to-service auth
- **Key Vault Integration**: Store all secrets in Azure Key Vault
- **Partition Key Design**: Design Cosmos DB partition keys for optimal performance
- **Function Bindings**: Use Azure Functions input/output bindings when possible

### Code Quality

- **TypeScript**: Full type safety across the application
- **Azure SDK Best Practices**: Follow official Azure SDK patterns
- **Error Handling**: Comprehensive error management with Azure diagnostics
- **Security**: Leverage Azure security features and best practices

### Development Workflow

- **Infrastructure as Code**: Use Azure Bicep for all infrastructure
- **Environment Isolation**: Separate dev/staging/prod environments
- **CI/CD Ready**: GitHub Actions workflows for Azure deployment
- **Monitoring First**: Implement logging and monitoring from day one

## 🆘 Troubleshooting

### Common Azure Issues

1. **Function App Deployment Fails**
   ```bash
   # Check deployment logs
   func azure functionapp logstream <function-app-name>
   
   # Verify requirements.txt
   cd server && pip install -r requirements.txt
   ```

2. **Cosmos DB Connection Issues**
   ```bash
   # Verify environment variables
   echo $COSMOS_DB_ENDPOINT
   echo $COSMOS_DB_KEY
   
   # Check firewall settings in Azure portal
   ```

3. **Key Vault Access Denied**
   ```bash
   # Verify managed identity has access
   az keyvault set-policy --name <vault-name> --object-id <managed-identity-id> --secret-permissions get list
   ```

4. **Static Web App Deployment Issues**
   ```bash
   # Check build configuration
   cd frontend && npm run build
   
   # Verify staticwebapp.config.json
   ```

### Debugging Tools

- **Azure Portal**: Monitor all services in one place
- **Application Insights**: Real-time error tracking and performance monitoring
- **Azure CLI**: Command-line troubleshooting and log access
- **Function App Logs**: Live streaming logs for debugging

### Support Resources

1. Check Azure Application Insights for detailed error logs
2. Use `func azure functionapp logstream` for real-time debugging
3. Review Azure service health status
4. Verify all environment variables and secrets are configured

## 🔄 Version History

### v2.0.0 - Azure Migration (Current)

- ✅ **Azure Functions**: Serverless backend with auto-scaling
- ✅ **Azure Cosmos DB**: NoSQL database with global distribution
- ✅ **Azure Static Web Apps**: Frontend hosting with CDN
- ✅ **Azure Key Vault**: Secure secrets management
- ✅ **One-Click Deployment**: Automated infrastructure provisioning
- ✅ **Free Tier Compatible**: Runs entirely on Azure free tier
- ✅ **Enhanced Security**: Azure Managed Identity and encrypted storage
- ✅ **Real-time Monitoring**: Application Insights integration

### v1.0.0 - Google Cloud Platform

- ✅ FastAPI backend on Google Cloud Run
- ✅ Firebase Firestore database
- ✅ Google Cloud Secret Manager
- ✅ Google OAuth authentication
- ✅ Plaid integration with encrypted token storage

## 💰 Cost Optimization

This application is designed to run on Azure's free tier:

- **Azure Functions**: 1M requests/month free
- **Azure Cosmos DB**: 1000 RU/s and 25GB free
- **Azure Static Web Apps**: Free tier with custom domains
- **Azure Key Vault**: 10,000 operations/month free
- **Application Insights**: 1GB data/month free

**Estimated monthly cost**: $0 - $5 for typical usage

## 📄 License

This project is open source and available under the MIT License.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Sage** - Bringing clarity to your financial future through intelligent financial management, now powered by Microsoft Azure.
