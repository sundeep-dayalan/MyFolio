# Personal Wealth Management API

A production-ready FastAPI application for comprehensive personal wealth management, featuring portfolio tracking, transaction management, and financial analytics with Firebase Firestore integration.

## Features

- 🔐 **Authentication**: Google OAuth integration with JWT tokens
- 👤 **User Management**: Complete user profile management
- 💼 **Portfolio Management**: Create and manage multiple investment portfolios
- 📊 **Asset Tracking**: Track various asset types (stocks, bonds, crypto, etc.)
- 💰 **Transaction Management**: Record and track buy/sell transactions
- 📈 **Analytics**: Portfolio performance and gain/loss calculations
- 🔒 **Security**: Production-ready security with proper input validation
- 📝 **Logging**: Comprehensive request/response logging
- 🧪 **Testing**: Comprehensive test suite
- 🐳 **Docker**: Containerized deployment ready

## Project Structure

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Application factory
│   ├── config.py              # Configuration management
│   ├── database.py            # Firebase connection
│   ├── dependencies.py        # Dependency injection
│   ├── exceptions.py          # Custom exceptions
│   ├── middleware/            # Custom middleware
│   ├── models/                # Pydantic models
│   ├── routers/               # API endpoints
│   ├── services/              # Business logic
│   └── utils/                 # Utilities
├── tests/                     # Test suite
├── docker/                    # Docker configuration
├── requirements.txt           # Dependencies
└── run.py                     # Entry point
```

## Quick Start

### Prerequisites

- Python 3.11+
- Firebase project with Firestore
- Service account credentials

### Installation

1. **Clone the repository**
   ```bash
   cd api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Add Firebase credentials**
   - Place your `service-account.json` file in the api directory
   - Update `FIREBASE_PROJECT_ID` in `.env`

6. **Run the application**
   ```bash
   python run.py
   ```

The API will be available at `http://localhost:8000`

### Development Setup

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run tests**
   ```bash
   pytest
   ```

3. **Format code**
   ```bash
   black .
   isort .
   ```

4. **Type checking**
   ```bash
   mypy .
   ```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key | Required |
| `FIREBASE_PROJECT_ID` | Firebase project ID | Required |
| `FIREBASE_CREDENTIALS_PATH` | Path to service account JSON | Required |
| `FIREBASE_DATABASE_ID` | Firestore database ID | `personal-wealth-management` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Required |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Required |
| `GOOGLE_REDIRECT_URI` | OAuth redirect URI | Auto-configured |
| `ENVIRONMENT` | Environment (development/production) | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Deployment

### Automatic Deployment (Recommended)

This project is configured for automatic deployment to Google Cloud Run via GitHub Actions.

**Prerequisites**: Configure GitHub repository secrets (see [GITHUB_ACTIONS_SETUP.md](../GITHUB_ACTIONS_SETUP.md))

**How it works**:
1. Push changes to the `api/` folder on the `main` branch
2. GitHub Actions automatically:
   - Runs tests
   - Builds and pushes Docker image
   - Deploys to Cloud Run
   - Runs health checks

**Production URL**: `https://myfolio-api-681015953939.us-central1.run.app`

### Manual Deployment

For manual deployment or local testing:

```bash
# Build and deploy
cd api
docker build --platform linux/amd64 -t gcr.io/fit-guide-465001-p3/myfolio-api .
docker push gcr.io/fit-guide-465001-p3/myfolio-api

# Deploy to Cloud Run
gcloud run deploy myfolio-api \
  --image gcr.io/fit-guide-465001-p3/myfolio-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 \
  --service-account myfolio-api-service@fit-guide-465001-p3.iam.gserviceaccount.com
```

## API Documentation

When running in development mode, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Main Endpoints

#### Authentication
- `POST /api/v1/auth/google` - Authenticate with Google
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user

#### Users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/{user_id}` - Update user

#### Wealth Management
- `POST /api/v1/wealth/portfolios` - Create portfolio
- `GET /api/v1/wealth/portfolios` - Get user portfolios
- `GET /api/v1/wealth/portfolios/{id}/summary` - Get portfolio summary
- `POST /api/v1/wealth/portfolios/{id}/holdings` - Add holding
- `POST /api/v1/wealth/portfolios/{id}/transactions` - Add transaction

## Docker Deployment

### Development
```bash
cd docker
docker-compose up --build
```

### Production
```bash
cd docker
docker-compose --profile production up --build
```

## Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_main.py
```

## Production Considerations

### Security
- Change `SECRET_KEY` to a secure random string
- Use strong Firebase security rules
- Enable HTTPS in production
- Restrict CORS origins
- Review and audit dependencies regularly

### Performance
- Use connection pooling for high-traffic scenarios
- Implement caching for frequently accessed data
- Monitor and optimize database queries
- Consider using async database drivers

### Monitoring
- Set up proper logging aggregation
- Implement health checks
- Monitor API performance metrics
- Set up alerts for errors and downtime

### Deployment
- Use environment-specific configuration
- Implement CI/CD pipelines
- Use container orchestration (Kubernetes, etc.)
- Set up database backups
- Configure proper resource limits

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Format code (`black . && isort .`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation at `/docs`
- Review the test cases for usage examples
# Updated Mon Aug  4 00:13:53 EDT 2025
