# MyFolio - Comprehensive Project Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [FastAPI Backend Flow](#fastapi-backend-flow)
4. [API Endpoints and Interconnections](#api-endpoints-and-interconnections)
5. [React Frontend Flow](#react-frontend-flow)
6. [Authentication Flow](#authentication-flow)
7. [Plaid Integration Flow](#plaid-integration-flow)
8. [Data Storage and Management](#data-storage-and-management)
9. [Security and Error Handling](#security-and-error-handling)
10. [Development and Deployment](#development-and-deployment)

---

## Project Overview

MyFolio is a comprehensive personal wealth management application that provides:
- Real-time financial data integration through Plaid
- Google OAuth 2.0 authentication
- Transaction tracking and categorization
- Account balance monitoring
- Portfolio management capabilities
- Production-ready deployment on Google Cloud Platform

**Core Technologies:**
- **Backend**: FastAPI + Python 3.12
- **Frontend**: React 19 + TypeScript + Vite
- **Database**: Firebase Firestore
- **Authentication**: Google OAuth 2.0
- **Financial Data**: Plaid API
- **Deployment**: Google Cloud Run + Firebase Hosting

---

## Architecture Overview

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   React Frontend    │◄──►│   FastAPI Backend   │◄──►│   External APIs     │
│   (Port 5173)       │    │   (Port 8000)       │    │                     │
├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤
│ • React Router      │    │ • OAuth Routes      │    │ • Google OAuth      │
│ • TanStack Query    │    │ • Plaid Routes      │    │ • Plaid API         │
│ • Auth Context      │    │ • Firestore Routes  │    │ • Firebase Auth     │
│ • Protected Routes  │    │ • Business Services │    │                     │
│ • UI Components     │    │ • JWT Auth          │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
                                       │
                                       ▼
                           ┌─────────────────────┐
                           │ Firebase Firestore  │
                           │                     │
                           │ • User Data         │
                           │ • Encrypted Tokens  │
                           │ • Account Data      │
                           │ • Transactions      │
                           └─────────────────────┘
```

---

## FastAPI Backend Flow

### Application Structure
```
api/app/
├── main.py              # Application entry point and FastAPI setup
├── config.py            # Environment configuration and settings
├── database.py          # Firebase/Firestore connection management
├── dependencies.py      # Dependency injection (JWT auth, user context)
├── exceptions.py        # Custom exception handling
├── middleware/          # CORS, logging, and error handling
├── models/              # Pydantic data models for validation
├── routers/             # API endpoint definitions
│   ├── oauth.py        # Google OAuth authentication routes
│   ├── plaid.py        # Plaid financial data integration
│   └── firestore.py    # Direct database operations
├── services/            # Business logic layer
│   ├── auth_service.py          # Authentication logic
│   ├── google_oauth_service.py  # Google OAuth implementation
│   ├── plaid_service.py         # Plaid API integration
│   ├── user_service.py          # User management
│   ├── account_storage_service.py    # Account data management
│   ├── transaction_storage_service.py # Transaction management
│   └── account_cache_service.py      # Caching layer
└── utils/               # Logging, security utilities
```

### Application Lifecycle
1. **Startup** (`main.py:lifespan`)
   - Initialize logging system
   - Connect to Firebase Firestore
   - Setup middleware and routers
   - Configure CORS and session management

2. **Request Processing**
   - CORS middleware handles cross-origin requests
   - Logging middleware tracks all requests
   - Session middleware manages OAuth state
   - Authentication dependency validates JWT tokens
   - Business services process requests
   - Exception handlers format error responses

3. **Shutdown**
   - Gracefully disconnect from Firebase
   - Clean up resources

---

## API Endpoints and Interconnections

### Authentication Flow (`/auth/oauth/*`)

#### 1. Google OAuth Initiation
**Endpoint**: `GET /api/v1/auth/oauth/google`
```
┌─────────────┐    GET /auth/oauth/google    ┌─────────────┐
│   Frontend  │ ─────────────────────────────► │   Backend   │
│             │                               │             │
│             │ ◄───── 302 Redirect ───────── │ OAuth URL   │
└─────────────┘    to Google OAuth            └─────────────┘
                                                      │
                                               ┌─────────────┐
                                               │   Google    │
                                               │   OAuth     │
                                               └─────────────┘
```

**Flow**:
- `AuthService.generate_google_auth_url()` creates OAuth URL
- Generates secure state parameter for CSRF protection
- Redirects user to Google's authorization server

#### 2. OAuth Callback Processing
**Endpoint**: `GET /api/v1/auth/oauth/google/callback`
```
┌─────────────┐    Callback with code    ┌─────────────┐    Exchange code    ┌─────────────┐
│   Google    │ ─────────────────────────► │   Backend   │ ──────────────────► │   Google    │
│   OAuth     │                           │             │                     │   API       │
└─────────────┘                           │             │ ◄────────────────── │             │
                                          │             │    User info        └─────────────┘
                                          │             │
                                          │             │    Store user       ┌─────────────┐
                                          │             │ ──────────────────► │  Firestore  │
                                          │             │                     │             │
                                          │             │ ◄────────────────── │             │
                                          │             │    User saved       └─────────────┘
                                          │             │
                                          │             │    Generate JWT     
                                          │             │ ──────────────────► │ JWT Token   │
                                          └─────────────┘                     └─────────────┘
```

**Services Used**:
- `GoogleOAuthService.exchange_code_for_tokens()` - Exchange authorization code
- `UserService.create_or_update_user()` - Store user data in Firestore
- `AuthService.create_access_token()` - Generate JWT token

### Plaid Integration Flow (`/plaid/*`)

#### 1. Link Token Creation
**Endpoint**: `POST /api/v1/plaid/create_link_token`
```
┌─────────────┐    Create Link Token    ┌─────────────┐    Link Token Request    ┌─────────────┐
│   Frontend  │ ─────────────────────► │   Backend   │ ─────────────────────────► │   Plaid     │
│             │   (with JWT)            │             │                           │   API       │
│             │ ◄───────────────────── │             │ ◄─────────────────────── │             │
└─────────────┘    Link Token          └─────────────┘    Link Token            └─────────────┘
```

**Dependencies**: Requires valid JWT token (`get_current_user_id`)
**Service**: `PlaidService.create_link_token()`

#### 2. Public Token Exchange
**Endpoint**: `POST /api/v1/plaid/exchange_public_token`
```
┌─────────────┐    Exchange Token       ┌─────────────┐    Exchange Request     ┌─────────────┐
│   Frontend  │ ─────────────────────► │   Backend   │ ─────────────────────► │   Plaid     │
│  (Plaid Link) │   public_token        │             │   public_token          │   API       │
│             │                         │             │ ◄───────────────────── │             │
│             │                         │             │   access_token          └─────────────┘
│             │                         │             │
│             │                         │             │   Encrypt & Store      ┌─────────────┐
│             │                         │             │ ─────────────────────► │  Firestore  │
│             │ ◄─────────────────────► │             │                        │             │
└─────────────┘    Success Response     └─────────────┘                        └─────────────┘
```

**Services Used**:
- `PlaidService.exchange_public_token()` - Exchange with Plaid
- `PlaidService.encrypt_token()` - Encrypt access token
- `UserService.store_plaid_token()` - Store in Firestore

#### 3. Account Data Retrieval (Cached)
**Endpoint**: `GET /api/v1/plaid/accounts` - Returns cached data for fast loading
```
┌─────────────┐    Get Accounts         ┌─────────────┐    Get User Tokens      ┌─────────────┐
│   Frontend  │ ─────────────────────► │   Backend   │ ─────────────────────► │  Firestore  │
│             │   (with JWT)            │             │                         │             │
│             │                         │             │ ◄───────────────────── │             │
│             │                         │             │   Encrypted Tokens     └─────────────┘
│             │                         │             │
│             │                         │             │   Decrypt & Fetch      ┌─────────────┐
│             │                         │             │ ─────────────────────► │   Plaid     │
│             │                         │             │                         │   API       │
│             │                         │             │ ◄───────────────────── │             │
│             │ ◄─────────────────────► │             │   Account Data          └─────────────┘
└─────────────┘    Account Data         └─────────────┘
```

**Services Used**:
- `AccountCacheService.get_cached_accounts()` - Retrieve cached data from Firestore
- `UserService.get_plaid_tokens()` - Retrieve encrypted tokens (if cache miss)
- `PlaidService.decrypt_token()` - Decrypt access tokens (if cache miss)
- `PlaidService.get_accounts()` - Fetch from Plaid API (if cache miss)
- `AccountStorageService.store_accounts()` - Cache in Firestore

**Caching Strategy**:
- First checks for cached account data in Firestore
- Returns cached data instantly if available and fresh (< 24 hours)
- Falls back to Plaid API only if cache is expired or missing
- **Cost Optimization**: Reduces Plaid API calls by 90-95%

#### 4. Transaction Synchronization
**Endpoint**: `GET /api/v1/plaid/transactions`
```
┌─────────────┐    Get Transactions     ┌─────────────┐    Background Sync      ┌─────────────┐
│   Frontend  │ ─────────────────────► │   Backend   │ ─────────────────────► │   Plaid     │
│             │   (with filters)        │             │                         │   API       │
│             │                         │             │ ◄───────────────────── │             │
│             │                         │             │   Transaction Data      └─────────────┘
│             │                         │             │
│             │                         │             │   Store/Update         ┌─────────────┐
│             │                         │             │ ─────────────────────► │  Firestore  │
│             │ ◄─────────────────────► │             │                        │             │
└─────────────┘    Paginated Results    └─────────────┘                        └─────────────┘
```

**Services Used**:
- `PlaidService.get_transactions()` - Fetch from Plaid
- `TransactionStorageService.store_transactions()` - Store in Firestore
- Background tasks for data synchronization

### Firestore Operations (`/firestore/*`)

#### Direct Database Access
**Endpoint**: `GET /api/v1/firestore/transactions`
```
┌─────────────┐    Query Transactions   ┌─────────────┐    Direct Query         ┌─────────────┐
│   Frontend  │ ─────────────────────► │   Backend   │ ─────────────────────► │  Firestore  │
│             │   (with pagination)     │             │                         │             │
│             │ ◄─────────────────────► │             │ ◄───────────────────── │             │
└─────────────┘    Paginated Data       └─────────────┘    Raw Data             └─────────────┘
```

**Features**:
- Pagination support
- Advanced filtering
- Direct Firestore queries for performance

---

## React Frontend Flow

### Application Structure
```
react-app/src/
├── App.tsx                  # Main routing and layout
├── main.tsx                 # Application entry point
├── components/
│   ├── ui/                  # Shadcn/UI base components
│   ├── custom/              # Feature-specific components
│   ├── layout/              # Layout components
│   └── ProtectedRoute.tsx   # Route guard component
├── pages/
│   ├── HomePage.tsx         # Dashboard with charts and data
│   ├── LoginPage.tsx        # Authentication page
│   ├── AccountsPage.tsx     # Account management
│   ├── TransactionsPage.tsx # Transaction history
│   └── OAuthCallback.tsx    # OAuth callback handler
├── services/
│   ├── AuthService.ts       # Authentication API calls
│   ├── PlaidService.ts      # Plaid integration API calls
│   └── FirestoreService.ts  # Direct Firestore queries
├── hooks/                   # Custom React hooks
├── context/                 # React context providers
├── types/                   # TypeScript type definitions
└── config/                  # Environment configuration
```

### Application Flow

#### 1. Application Initialization
```
main.tsx → App.tsx → React Router → Route Protection
```

**Entry Point** (`main.tsx`):
- Initialize React application
- Setup TanStack Query for state management
- Mount App component

**Main App** (`App.tsx`):
- Define routes with React Router
- Wrap protected routes with `ProtectedRoute`
- Setup layout components
- Configure toast notifications

#### 2. Authentication Flow
```
┌─────────────┐    Check Auth State     ┌─────────────┐    Load User Data       ┌─────────────┐
│ Route Guard │ ─────────────────────► │ Auth Context│ ─────────────────────► │ Local Storage│
│             │                         │             │                         │             │
│             │ ◄─────────────────────► │             │ ◄───────────────────── │             │
└─────────────┘    Auth Status          └─────────────┘    Token/User           └─────────────┘
                       │
                       ▼
               ┌─────────────┐
               │   Redirect  │
               │ Login/Home  │
               └─────────────┘
```

**Protected Route Logic**:
- Check for valid JWT token in localStorage
- Validate token expiration
- Redirect to login if unauthenticated
- Load user context for authenticated users

#### 3. Page-Level Data Flow

**Dashboard (HomePage)**:
```
┌─────────────┐    useQuery Hook        ┌─────────────┐    API Calls            ┌─────────────┐
│  HomePage   │ ─────────────────────► │TanStack Query│ ─────────────────────► │   Backend   │
│             │                         │             │                         │   APIs      │
│             │ ◄─────────────────────► │             │ ◄───────────────────── │             │
└─────────────┘    Cached Data          └─────────────┘    Real-time Data       └─────────────┘
```

- Uses TanStack Query for server state management
- Automatic background refetching
- Optimistic updates
- Error boundary handling

**Accounts Page (with Caching)**:
```
┌─────────────┐    Load Cached Data     ┌─────────────┐    Check Cache          ┌─────────────┐
│AccountsPage │ ─────────────────────► │PlaidService │ ─────────────────────► │  Firestore  │
│             │                         │             │                         │   Cache     │
│             │ ◄─────────────────────► │             │ ◄───────────────────── │             │
│             │    Instant Data         │             │    Cached Data          └─────────────┘
│             │                         │             │
│             │    Manual Refresh       │             │    Fetch Fresh Data     ┌─────────────┐
│             │ ─────────────────────► │             │ ─────────────────────► │ Plaid API   │
│             │                         │             │                         │             │
│             │ ◄─────────────────────► │             │ ◄───────────────────── │             │
└─────────────┘    Updated Data         └─────────────┘    Fresh Data           └─────────────┘
```

**Features**:
- **AccountsRefreshCard Component**: Shows cache status and refresh controls
- **Instant Loading**: Primary data loads from Firestore cache
- **Manual Refresh**: User-triggered refresh from Plaid API
- **Cache Status Indicators**: Visual indicators for data freshness
- **Cost Savings**: 90-95% reduction in Plaid API calls
- Integrates React Plaid Link component for new connections
- Handles token exchange flow
- Real-time account balance updates

**Transactions Page**:
```
┌─────────────┐    Paginated Query      ┌─────────────┐    Background Sync      ┌─────────────┐
│TransactionsPage│ ───────────────────► │FirestoreService│ ──────────────────► │   Backend   │
│             │                         │             │                         │   Sync      │
│             │ ◄─────────────────────► │             │ ◄───────────────────── │             │
└─────────────┘    Real-time Updates    └─────────────┘    Fresh Data          └─────────────┘
```

- Infinite scroll pagination
- Real-time transaction updates
- Advanced filtering and search

### State Management

#### Authentication State
```
AuthContext → localStorage ↔ JWT Token
                    ↓
            User Authentication State
                    ↓
            Protected Route Access
```

#### Server State (TanStack Query)
```
API Queries → Cache Layer → Background Refetch → UI Updates
     ↓
Optimistic Updates → Immediate UI → Revert on Error
```

#### Local State
- Component-level state with useState
- Form state management
- UI interaction state

---

## Authentication Flow

### Complete OAuth 2.0 Flow
```
1. User clicks "Login with Google"
   Frontend: AuthService.initiateGoogleLogin()
   ↓
2. Redirect to Backend OAuth endpoint
   GET /api/v1/auth/oauth/google
   ↓
3. Backend generates secure OAuth URL
   AuthService.generate_google_auth_url()
   ↓
4. Redirect to Google OAuth consent screen
   User authorizes application
   ↓
5. Google redirects to backend callback
   GET /api/v1/auth/oauth/google/callback?code=...
   ↓
6. Backend exchanges code for tokens
   GoogleOAuthService.exchange_code_for_tokens()
   ↓
7. Fetch user info from Google API
   GoogleOAuthService.get_user_info()
   ↓
8. Store/update user in Firestore
   UserService.create_or_update_user()
   ↓
9. Generate JWT access token
   AuthService.create_access_token()
   ↓
10. Redirect to frontend with token
    Frontend: AuthService.handleOAuthCallback()
    ↓
11. Store token and user data
    localStorage: token, user info
    ↓
12. Redirect to dashboard
    Navigate to /home
```

### JWT Token Management
- **Token Generation**: HS256 algorithm with configurable expiration
- **Token Validation**: Middleware validates every protected request
- **Token Storage**: Secure storage in localStorage
- **Token Refresh**: Automatic refresh before expiration

---

## Plaid Integration Flow

### Account Connection Flow
```
1. User initiates bank connection
   Frontend: PlaidService.createLinkToken()
   ↓
2. Backend requests Plaid Link token
   PlaidService.create_link_token()
   ↓
3. Frontend displays Plaid Link component
   React Plaid Link integration
   ↓
4. User completes bank authentication
   Plaid Link returns public_token
   ↓
5. Exchange public token for access token
   PlaidService.exchangePublicToken()
   ↓
6. Backend encrypts and stores access token
   PlaidService.encrypt_token() + UserService.store_plaid_token()
   ↓
7. Fetch initial account data
   PlaidService.get_accounts()
   ↓
8. Store account data in Firestore
   AccountStorageService.store_accounts()
   ↓
9. Display accounts in frontend
   Real-time account balance updates
```

### Transaction Synchronization
```
Scheduled Background Job:
1. Fetch stored access tokens for all users
   UserService.get_all_plaid_tokens()
   ↓
2. For each user, sync transactions
   PlaidService.sync_transactions()
   ↓
3. Store new/updated transactions
   TransactionStorageService.store_transactions()
   ↓
4. Update account balances
   AccountStorageService.update_balances()
   ↓
5. Cache latest data for fast retrieval
   AccountCacheService.cache_account_data()
```

### Data Refresh Strategies
- **Cached Data**: Primary data source from Firestore (instant loading)
- **Real-time**: Webhook-based updates (production)
- **Scheduled**: Background sync jobs
- **On-demand**: User-triggered refresh
- **Force refresh**: Full data resynchronization via `POST /api/v1/plaid/accounts/refresh`

#### Cache Management Endpoints
- `GET /api/v1/plaid/accounts` - Returns cached data (fast, no API cost)
- `POST /api/v1/plaid/accounts/refresh` - Force refresh from Plaid API
- `GET /api/v1/plaid/accounts/cache-info` - Get cache metadata and status

---

## Data Storage and Management

### Firestore Database Schema
```
/users/{user_id}
├── /user_info
│   ├── email: string
│   ├── name: string
│   ├── picture: string
│   ├── created_at: timestamp
│   └── last_login: timestamp
├── /plaid_tokens
│   ├── access_tokens: {item_id: encrypted_token}
│   ├── item_ids: string[]
│   └── updated_at: timestamp
├── /accounts/{user_id}           # Cached account data collection
│   ├── user_id: string
│   ├── accounts: PlaidAccount[]
│   ├── total_balance: number
│   ├── account_count: number
│   ├── last_updated: timestamp
│   ├── data_source: "plaid_api"
│   └── created_at: timestamp
└── /transactions/{transaction_id}
    ├── transaction_data: TransactionData
    ├── category: string[]
    ├── account_id: string
    └── date: timestamp
```

### Data Access Patterns

#### 1. User Data Management
```
UserService Methods:
- create_or_update_user()     # OAuth registration/login
- get_user_by_id()           # Profile retrieval
- update_user_profile()      # Profile updates
- store_plaid_token()        # Token storage
- get_plaid_tokens()         # Token retrieval
```

#### 2. Account Data Management
```
AccountCacheService Methods:
- get_cached_accounts()      # Retrieve cached data from Firestore
- store_account_cache()      # Store account data in cache
- is_cache_valid()          # Check if cache is fresh (< 24 hours)
- get_cache_metadata()      # Get cache status and timestamps
- clear_cache()             # Remove expired cache data

AccountStorageService Methods:
- store_accounts()           # Bulk account storage
- get_user_accounts()        # Retrieve user accounts
- update_account_balance()   # Balance updates
- cache_account_summary()    # Performance optimization
```

#### 3. Transaction Management
```
TransactionStorageService Methods:
- store_transactions()       # Bulk transaction storage
- get_paginated_transactions() # Paginated retrieval
- update_transaction()       # Individual updates
- delete_transactions()      # Cleanup operations
```

### Multi-Level Caching Strategy

#### 1. Database Caching (Primary)
- **AccountCacheService**: Stores account data in Firestore for 24+ hours
- **Cost Optimization**: Reduces Plaid API calls by 90-95%
- **Performance**: Instant loading from cached data
- **Cache Expiration**: Configurable 24-hour default

#### 2. Application Level Caching
- **TanStack Query**: Client-side caching and state management
- **Optimistic Updates**: Immediate UI updates with background sync
- **Background Refetch**: Automatic data refresh

#### 3. Service Level Caching
- **AccountCacheService**: Server-side data caching layer
- **Cache Validation**: Automatic expiration and refresh logic
- **Fallback Strategy**: Graceful degradation to Plaid API

#### 4. Infrastructure Caching
- **Firestore**: Built-in database caching
- **CDN**: Static asset caching for frontend
- **Browser Cache**: Client-side asset caching

#### Cache Flow Optimization
```
1. User Request → Check Firestore Cache
2. Cache Hit (Fresh) → Return Instant Data
3. Cache Miss/Expired → Fetch from Plaid API
4. Store in Cache → Return Data
5. Subsequent Requests → Instant Cache Response
```

---

## Security and Error Handling

### Security Measures

#### 1. Authentication Security
- **OAuth 2.0**: Industry-standard authentication
- **JWT Tokens**: Stateless authentication with configurable expiration
- **CSRF Protection**: State parameter in OAuth flow
- **Secure Sessions**: HTTPOnly cookies for session management

#### 2. Data Protection
- **Token Encryption**: Fernet encryption for Plaid access tokens
- **Environment Variables**: Secure configuration management
- **HTTPS Only**: All communications over secure connections
- **Input Validation**: Pydantic models for request validation

#### 3. Access Control
- **User Isolation**: Firestore security rules prevent cross-user access
- **JWT Validation**: Every protected endpoint validates tokens
- **Route Protection**: Frontend route guards
- **API Rate Limiting**: Protection against abuse

### Error Handling

#### Backend Error Handling
```
Exception Hierarchy:
├── AuthenticationError     # JWT/OAuth failures
├── ValidationError        # Input validation failures
├── PlaidError            # Plaid API errors
├── FirestoreError        # Database errors
└── HTTPException         # Generic HTTP errors

Error Response Format:
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid"
}
```

#### Frontend Error Handling
```
Error Boundary → Component Level Error Handling
     ↓
TanStack Query Error → Automatic Retry + User Notification
     ↓
Form Validation → Field-level Error Display
     ↓
Network Errors → Toast Notifications + Offline Handling
```

### Monitoring and Logging
- **Structured Logging**: JSON-formatted logs for analysis
- **Request Tracking**: Unique request IDs for tracing
- **Error Monitoring**: Comprehensive error logging
- **Performance Metrics**: Response times and throughput

---

## Development and Deployment

### Development Workflow
```
1. Local Development
   ├── Backend: python run.py (port 8000)
   ├── Frontend: npm run dev (port 5173)
   └── Database: Firebase Firestore (development project)

2. Code Quality
   ├── Backend: black, flake8, mypy, pytest
   ├── Frontend: prettier, eslint, npm run build
   └── Git hooks: Pre-commit validation

3. Testing
   ├── Unit Tests: pytest (backend), jest (frontend)
   ├── Integration Tests: API endpoint testing
   └── E2E Tests: Full user flow testing
```

### Production Deployment
```
1. Backend (Google Cloud Run)
   ├── Docker containerization
   ├── Environment variable configuration
   ├── Automatic scaling
   └── Health check endpoints

2. Frontend (Firebase Hosting)
   ├── Vite production build
   ├── Static asset optimization
   ├── CDN distribution
   └── Custom domain configuration

3. Database (Firebase Firestore)
   ├── Production security rules
   ├── Backup configuration
   ├── Index optimization
   └── Monitoring setup
```

### Configuration Management
```
Environment Variables:
Backend (.env):
- SECRET_KEY, FIREBASE_PROJECT_ID
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
- PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV

Frontend (.env.production):
- VITE_API_BASE_URL
- VITE_APP_ENV
```

---

## Production Features and Optimizations

### Account Data Caching System

**Implementation Status**: ✅ **Complete and Production Ready**

The application features an intelligent caching system that significantly reduces Plaid API costs while providing instant data loading:

#### Key Features
- **AccountsRefreshCard Component**: Beautiful UI showing cache status with visual indicators
  - 🟢 Green: Current data (< 2 hours old)
  - 🟠 Orange: Outdated data (> 2 hours, < 24 hours)
  - 🟡 Yellow: Missing cache data
- **Human-readable timestamps**: "2 minutes ago", "3 hours ago" format
- **Cache age display**: Shows precise age in hours
- **One-click refresh**: Manual refresh button with loading states
- **Account summary**: Shows count and total balance from cached data

#### Technical Implementation
- **24-hour cache expiration**: Configurable cache duration
- **User-specific storage**: Each user's data isolated in Firestore
- **Metadata tracking**: Last updated, created at, data source tracking
- **Error handling**: Graceful degradation when cache fails
- **Smart fallback**: Falls back to Plaid API when cache is expired

#### Cost Optimization Results
**Before Caching**:
- Every accounts page visit = Plaid API call
- 100 users × 10 visits/day = 1,000 API calls/day
- High operational costs

**After Caching**:
- Initial connection = 1 API call (cached for 24+ hours)
- Regular usage = 0 API calls (served from cache)
- Only refresh when user explicitly requests
- **Result: 90-95% reduction in API calls** 🎯

#### API Endpoints
- `GET /api/v1/plaid/accounts` - Returns cached data (fast, no API cost)
- `POST /api/v1/plaid/accounts/refresh` - Force refresh from Plaid API
- `GET /api/v1/plaid/accounts/cache-info` - Get cache metadata and status

#### Cache Flow
```
1. User connects bank → Data cached in Firestore (24+ hour expiration)
2. Regular usage → Load from cache (instant, no API cost)
3. Manual refresh → Fresh data from Plaid → Cache updated
4. Subsequent visits → Instant loading from cache
```

#### Developer Experience
- **Clean API design**: Intuitive endpoint structure
- **Comprehensive logging**: Detailed logs for debugging
- **Type safety**: Full TypeScript support
- **React Query integration**: Optimistic updates and intelligent caching
- **Error boundaries**: Proper error handling throughout

---

## Summary

This comprehensive documentation covers the complete MyFolio application flow, from user authentication through data synchronization. The application follows modern best practices with:

- **Layered Architecture**: Clear separation between presentation, business logic, and data layers
- **Security First**: OAuth 2.0, JWT tokens, encrypted storage, and input validation
- **Production Ready**: Scalable deployment, monitoring, error handling, and performance optimization
- **Developer Experience**: Type safety, code quality tools, and comprehensive testing

The interconnected flow ensures secure, real-time financial data management while maintaining excellent user experience and system reliability.