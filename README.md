# Sage - Financial Management Application

## 🚀 One-Click Deployment

Deploy Sage to Google Cloud in just 5-10 minutes with a single click!

### Quick Start

#### Step 1: Get Your Own Copy
1. **Fork this repository** to your GitHub account (click "Fork" button above)
2. **Customize if needed** - edit branding, colors, features in your fork

#### Step 2: Deploy to Google Cloud
1. **Update the deployment URL** in your fork's README.md:
   - Replace `YOUR_USERNAME` with your GitHub username
   - Commit the change to your fork

2. **Click your deployment button**:
```markdown
[![Deploy to Google Cloud](https://deploy.cloud.run/button.svg)](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/YOUR_USERNAME/personal-wealth-management.git&cloudshell_working_dir=.&cloudshell_tutorial=TUTORIAL.md)
```

#### Step 3: Automated Setup
3. **Follow the interactive Cloud Shell tutorial**
4. **Configure your app name and settings**
5. **Watch as everything deploys automatically**
6. **Set up Plaid and OAuth credentials** (5 minutes)
7. **Start managing your finances!**

> **💡 Pro Tip**: You can customize the app before deploying by editing your fork. Change app name, colors, features, or add your own branding!

**What gets deployed:**
- ✅ FastAPI backend on Cloud Run
- ✅ React frontend on Cloud Run  
- ✅ Firestore database with security rules
- ✅ Google OAuth integration
- ✅ Service accounts and IAM roles
- ✅ Budget alerts and monitoring
- ✅ SSL certificates and custom domains

**Total cost:** ~$5-15/month (includes $10 budget alert)

### 🎯 Why Fork First?

- **🔐 Your Data, Your Control**: Deploy to your own GCP account with full control
- **🎨 Customization Freedom**: Modify the app before deploying - add features, change branding
- **🔄 Easy Updates**: Pull updates from the main repo when new features are released
- **📈 Your Infrastructure**: Own your deployment, scale as needed, add your own features
- **🛡️ Security**: Your financial data stays in your Google Cloud account only

---

## 🌟 Overview

Sage is a comprehensive financial management application that integrates with Plaid to provide real-time financial data analysis, transaction tracking, and portfolio management. The application features a modern React frontend with a robust FastAPI backend, all designed for production deployment on Google Cloud Platform.

## 🏗️ Architecture

### System Architecture

```
Frontend (React + TypeScript)
├── Vite Build System
├── React Query for State Management
├── React Router for Navigation
└── Tailwind CSS for Styling

Backend (FastAPI + Python)
├── Layered Architecture
├── JWT Authentication
├── Firebase/Firestore Database
├── Google Cloud Run Deployment
└── Plaid Integration

External Services
├── Plaid API (Financial Data)
├── Google OAuth (Authentication)
├── Firebase (Database & Auth)
└── Google Cloud Platform (Deployment)
```

### Project Structure

```
personal-wealth-management/
├── server/                       # Backend FastAPI application
│   ├── app/                      # Main application package
│   │   ├── main.py              # Application factory and startup
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # Firebase/Firestore connection
│   │   ├── dependencies.py      # Dependency injection
│   │   ├── exceptions.py        # Custom exception classes
│   │   ├── middleware/          # Custom middleware
│   │   ├── models/              # Pydantic models
│   │   ├── routers/             # API endpoint routes
│   │   ├── services/            # Business logic layer
│   │   └── utils/               # Utility functions
│   ├── requirements.txt         # Production dependencies
│   ├── requirements-dev.txt     # Development dependencies
│   ├── Dockerfile              # Container definition
│   └── run.py                  # Application entry point
└── frontend/                    # Frontend React application
    ├── components/             # Reusable React components
    ├── pages/                  # Page components
    ├── services/              # API service layer
    ├── context/               # React context providers
    ├── hooks/                 # Custom React hooks
    ├── config/                # Configuration files
    └── types.ts               # TypeScript type definitions
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

- **FastAPI**: Modern Python web framework
- **Python 3.12+**: Latest Python features
- **Pydantic**: Data validation and settings management
- **Firebase Admin SDK**: Database and authentication
- **Plaid Python SDK**: Financial data integration
- **JWT**: Secure token-based authentication

### Infrastructure

- **Google Cloud Run**: Serverless container deployment
- **Firebase Firestore**: NoSQL document database
- **Google Cloud Build**: CI/CD pipeline
- **Docker**: Containerization

## 🔧 Installation & Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Google Cloud Platform account
- Firebase project
- Plaid developer account

### Backend Setup

1. **Navigate to API directory**

   ```bash
   cd server
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   ```bash
   cp .env.template .env
   # Edit .env with your credentials
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

### Frontend Setup

1. **Navigate to React app directory**

   ```bash
   cd frontend
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Configure environment**

   ```bash
   cp .env.template .env.development
   # Edit environment files as needed
   ```

4. **Run development server**
   ```bash
   npm run dev
   ```

## 🌐 Deployment

### 🚀 One-Click Deployment (Recommended)

The fastest way to deploy Sage is using our automated deployment system:

1. **Click the deployment button** at the top of this README
2. **Follow the interactive tutorial** in Google Cloud Shell
3. **Complete post-deployment setup** for Plaid and OAuth credentials

### Manual Deployment

For advanced users who want to customize the deployment:

1. **Backend Deployment** (Google Cloud Run)

   ```bash
   cd server
   gcloud run deploy sage-backend --source .
   ```

2. **Frontend Deployment** (Google Cloud Run)
   ```bash
   cd frontend
   gcloud run deploy sage-frontend --source .
   ```

### Deployment Architecture

```
Google Cloud Platform
├── Cloud Run (Backend API)
├── Cloud Run (Frontend SPA)
├── Firestore (Database)
├── Secret Manager (API Keys)
├── IAM & Service Accounts
└── Cloud Monitoring & Logging
```

### Environment Configuration

#### Backend (.env)

```bash
# Application Settings
DEBUG=false
ENVIRONMENT=production

# Security Configuration
SECRET_KEY=your-production-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=service-account.json

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=your-redirect-uri

# Plaid Configuration
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=production
```

#### Frontend (.env.production)

```bash
VITE_API_BASE_URL=https://your-server-domain/api/v1
VITE_APP_ENV=production
```

## 🔐 Security

### Authentication & Authorization

- **Google OAuth 2.0**: Secure user authentication
- **JWT Tokens**: Stateless authentication with configurable expiration
- **Token Encryption**: Access tokens encrypted using Fernet encryption
- **Secure Storage**: Encrypted tokens stored in Firebase Firestore

### API Security

- **CORS Configuration**: Proper cross-origin request handling
- **Input Validation**: Comprehensive request validation with Pydantic
- **Error Handling**: Secure error responses without sensitive data exposure
- **Rate Limiting**: Built-in protection against abuse

### Data Protection

- **Encryption at Rest**: Sensitive data encrypted in database
- **HTTPS Only**: All communications over secure connections
- **Environment Variables**: Secure configuration management
- **Access Controls**: User-specific data isolation

## 📊 API Documentation

### Authentication Endpoints

- `POST /auth/google/login` - Google OAuth login
- `POST /auth/refresh` - Refresh JWT token
- `POST /auth/logout` - User logout

### Plaid Integration Endpoints

- `POST /plaid/create_link_token` - Create Plaid Link tokens
- `POST /plaid/exchange_public_token` - Exchange and store access tokens
- `GET /plaid/accounts` - Get account balances
- `GET /plaid/transactions` - Retrieve transactions

### User Management

- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update user profile
- `DELETE /users/me` - Delete user account

### Health & Monitoring

- `GET /health` - Application health check
- `GET /api/v1/docs` - Interactive API documentation

## 🧪 Testing

### Backend Testing

```bash
cd server
pytest tests/
```

### Frontend Testing

```bash
cd react-app
npm test
```

### Integration Testing

The application includes comprehensive testing for:

- Plaid integration flows
- Authentication mechanisms
- API endpoints
- Database operations

## 📈 Monitoring & Logging

### Application Monitoring

- **Structured Logging**: JSON-formatted logs for analysis
- **Request Tracking**: Unique request IDs for tracing
- **Error Monitoring**: Comprehensive error logging and alerting
- **Performance Metrics**: Response times and throughput monitoring

### Health Checks

- **API Health**: Built-in health check endpoints
- **Database Connectivity**: Firebase connection monitoring
- **External Service Status**: Plaid API availability checks

## 🔮 Production Optimization

### Performance Features

- **Query Optimization**: Efficient Firestore queries with fallback strategies
- **Connection Pooling**: Optimized Firebase connection management
- **Caching Strategy**: Client-side data storage with React Query
- **Bundle Optimization**: Tree shaking and code splitting

### Scalability

- **Horizontal Scaling**: Stateless API design for scaling
- **Database Indexing**: Optimized Firestore indexes for performance
- **CDN Integration**: Static asset delivery optimization
- **Load Balancing**: Google Cloud Load Balancer support

## 📚 Development Guidelines

### Code Quality

- **TypeScript**: Full type safety across the application
- **Linting**: ESLint and Pylint for code consistency
- **Formatting**: Prettier and Black for code formatting
- **Testing**: Comprehensive test coverage

### Best Practices

- **Separation of Concerns**: Layered architecture
- **Error Handling**: Comprehensive error management
- **Security First**: Security considerations in all development
- **Documentation**: Inline documentation and API specs

## 🆘 Troubleshooting

### Common Issues

1. **Firebase Connection Issues**

   - Verify service account credentials
   - Check Firestore rules and indexes

2. **Plaid Integration Problems**

   - Confirm API keys and environment settings
   - Review sandbox vs production configuration

3. **Authentication Failures**
   - Validate Google OAuth configuration
   - Check JWT secret and expiration settings

### Support

For issues and questions:

1. Check the logs for detailed error messages
2. Review the API documentation at `/api/v1/docs`
3. Verify environment configuration
4. Check external service status (Plaid, Firebase)

## 🔄 Version History

### Latest Production Release

- ✅ Full Plaid integration with production-ready token management
- ✅ Google OAuth authentication
- ✅ Firebase Firestore database integration
- ✅ Encrypted token storage
- ✅ Production-optimized error handling
- ✅ Comprehensive logging and monitoring
- ✅ Docker containerization
- ✅ Google Cloud deployment ready

## 📄 License

This project is private and proprietary.

## 👥 Contributing

This is a personal project. For internal development guidelines, please refer to the development documentation.

---

**Sage** - Bringing clarity to your financial future through intelligent financial management.
