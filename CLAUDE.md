# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MyFolio is a personal wealth management application with a React frontend and FastAPI backend that integrates with Plaid for financial data. The application uses Google OAuth for authentication and Firebase Firestore for data storage.

## Development Commands

### Backend (Server)

**Port Management**: Backend runs on port 8000. Always check if port is busy before starting:

```bash
# Check if port 8000 is busy
lsof -ti:8000 | xargs kill -9  # Kill process if busy
```

- Start development server: `cd server && python3 run.py`
- Alternative with uvicorn reload: `cd server && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Install dependencies: `cd server && pip3 install -r requirements.txt`
- Install dev dependencies: `cd server && pip3 install -r requirements-dev.txt`
- Run tests: `cd server && pytest tests/`
- Code formatting: `cd server && black .`
- Linting: `cd server && flake8`
- Type checking: `cd server && mypy .`

### Frontend

**Port Management**: Frontend runs on http://localhost:5173/. Check if port is busy before starting:

```bash
# Check if port 5173 is busy
lsof -ti:5173 | xargs kill -9  # Kill process if busy
```

- Start development server: `cd frontend && npm run dev` (runs on http://localhost:5173/)
- Install dependencies: `cd frontend && npm install`
- Build for production: `cd frontend && npm run build`
- Lint code: `cd frontend && npm run lint`
- Preview build: `cd frontend && npm run preview`

## Architecture

### Backend Structure

```
server/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment configuration
│   ├── database.py          # Firebase/Firestore connection
│   ├── routers/             # API endpoints
│   │   ├── oauth.py         # Google OAuth authentication
│   │   ├── plaid.py         # Plaid financial data integration
│   │   └── firestore.py     # Database operations
│   ├── services/            # Business logic layer
│   │   ├── auth_service.py
│   │   ├── plaid_service.py
│   │   ├── account_storage_service.py
│   │   └── transaction_storage_service.py
│   ├── models/              # Pydantic data models
│   ├── middleware/          # CORS, logging, error handling
│   └── utils/               # Security, logging utilities
└── run.py                   # Development server entry point
```

### Frontend Structure

```
frontend/src/
├── App.tsx                  # Main app component with routing
├── components/
│   ├── ui/                  # Shadcn/UI components
│   ├── custom/              # Feature-specific components
│   │   ├── accounts/        # Account-related UI
│   │   └── transactions/    # Transaction-related UI
│   ├── layout/              # Layout components
│   └── ProtectedRoute.tsx   # Route protection
├── pages/                   # Page components
├── services/                # API service layer
├── hooks/                   # Custom React hooks
├── context/                 # React context providers
└── types/                   # TypeScript definitions
```

## Key Technologies

### Backend

- **FastAPI**: Modern Python web framework
- **Firebase Admin SDK**: Database and authentication
- **Plaid Python SDK**: Financial data integration
- **Pydantic**: Data validation and settings
- **Python-JOSE**: JWT token handling
- **Cryptography**: Token encryption

### Frontend

- **React 19**: Latest React with modern hooks
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **React Router**: Client-side routing
- **TanStack Query**: Server state management
- **Tailwind CSS**: Utility-first styling
- **Shadcn/UI**: Component library
- **React Plaid Link**: Plaid integration

## Authentication Flow

1. User initiates Google OAuth login
2. Backend exchanges OAuth code for Google tokens
3. User info stored in Firebase with encrypted Plaid tokens
4. JWT tokens issued for API authentication
5. Protected routes require valid JWT tokens

## Plaid Integration

- **Link Token Creation**: Dynamic product selection and account filters
- **Token Exchange**: Secure storage of encrypted access tokens
- **Account Data**: Real-time balance and position retrieval
- **Transactions**: Categorized transaction history with filtering

## Database Schema (Firestore)

```
users/{user_id}
├── user_info: {email, name, oauth_tokens}
├── plaid_tokens: {encrypted_access_tokens, item_ids}
├── accounts/{account_id}: {account_data, balances}
└── transactions/{transaction_id}: {transaction_details}
```

## Environment Variables

### Backend (.env)

```
SECRET_KEY=your-jwt-secret
FIREBASE_PROJECT_ID=your-project-id
GOOGLE_CLIENT_ID=your-oauth-client-id
GOOGLE_CLIENT_SECRET=your-oauth-secret
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=sandbox|production
```

### Frontend (.env.development)

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_ENV=development
```

## Testing

- Backend uses pytest with async support
- No frontend test setup currently configured
- Integration tests cover Plaid flows and auth

## Common Development Tasks

- **Adding new API endpoints**: Create in `server/app/routers/`
- **Adding new React components**: Use existing patterns in `frontend/src/components/`
- **Database operations**: Use services in `server/app/services/`
- **Frontend API calls**: Use hooks in `frontend/src/hooks/`

## Security Considerations

- All Plaid access tokens are encrypted before storage - For now for dev puposes the encrupt and decrypt method directly retuns the str. Once we go to prod, we will enfore encryption and deceryptipon
- JWT tokens have configurable expiration
- CORS properly configured for frontend domains
- Input validation on all API endpoints
- User data isolation in Firestore

## Production Deployment

- Backend: Google Cloud Run with Docker
- Frontend: Firebase Hosting
- Database: Firebase Firestore
- Authentication: Google OAuth 2.0

## Plaid Integration Guidelines

- **Primary Reference**: See `docs/PLAID.md` for complete Plaid documentation, endpoints, and best practices
- Always use the official Plaid docs referenced in `docs/PLAID.md`
- Follow the api endpoints and request response models in plaid documentation reference links added in `docs/PLAID.md`
