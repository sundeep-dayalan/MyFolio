# Plaid Token Lifecycle Management

## Overview

This system provides comprehensive lifecycle management for Plaid access tokens stored in Firebase Firestore. It ensures that expired, stale, and unused tokens are properly cleaned up to maintain security and database hygiene.

## Features

### 🧹 Automatic Cleanup

- **Expired Tokens**: Automatically removes tokens marked as expired or revoked
- **Stale Tokens**: Removes tokens that haven't been used for a configurable period (default: 90 days)
- **Invalid Tokens**: Validates tokens with Plaid API and marks invalid ones as expired
- **Scheduled Cleanup**: Daily automated cleanup at 2 AM via APScheduler

### 📊 Analytics & Monitoring

- Real-time token health analytics
- Institution distribution tracking
- Environment usage statistics
- Stale token identification (30 and 90-day thresholds)

### 🔐 User Token Management

- Revoke individual tokens per user
- Revoke all tokens for a user
- Automatic token usage tracking
- Production-ready token validation

## API Endpoints

### Token Cleanup

```http
DELETE /api/v1/plaid/tokens/cleanup?days_threshold=90
```

Clean up expired and stale tokens system-wide. Requires authentication.

**Parameters:**

- `days_threshold` (optional): Number of days of inactivity before considering a token stale (default: 90)

**Response:**

```json
{
  "message": "Token cleanup completed",
  "statistics": {
    "total_checked": 15,
    "expired_removed": 3,
    "stale_removed": 2,
    "invalid_marked": 1,
    "revoked_removed": 1,
    "total_cleaned": 6
  }
}
```

### Revoke All User Tokens

```http
DELETE /api/v1/plaid/tokens/revoke-all
```

Revoke all active tokens for the authenticated user.

**Response:**

```json
{
  "message": "Revoked 3 tokens successfully",
  "revoked_count": 3
}
```

### Token Analytics

```http
GET /api/v1/plaid/tokens/analytics
```

Get comprehensive token analytics and health information.

**Response:**

```json
{
  "analytics": {
    "total_tokens": 25,
    "active_tokens": 18,
    "expired_tokens": 4,
    "revoked_tokens": 3,
    "unique_users": 12,
    "stale_tokens_30_days": 2,
    "stale_tokens_90_days": 5,
    "institutions": {
      "Chase Bank": 8,
      "Bank of America": 5,
      "Wells Fargo": 3
    },
    "environments": {
      "sandbox": 20,
      "production": 5
    }
  }
}
```

### Revoke Individual Token

```http
DELETE /api/v1/plaid/items/{item_id}
```

Revoke a specific Plaid item/token for the authenticated user.

## Command Line Interface

### Installation

```bash
# Install required dependencies
pip install APScheduler

# Make the script executable
chmod +x manage_tokens.py
```

### Usage

#### Clean up expired tokens

```bash
python manage_tokens.py cleanup --days 90
```

#### View token analytics

```bash
python manage_tokens.py analytics
```

#### Revoke all tokens for a user

```bash
python manage_tokens.py revoke <user_id>
```

### Example Output

```
🚀 Personal Wealth Management - Token Management
==================================================
🧹 Token Cleanup Results:
   Total tokens checked: 15
   Expired tokens removed: 3
   Stale tokens removed: 2
   Invalid tokens marked: 1
   Revoked tokens removed: 1
   Total cleaned: 6
```

## Token Data Structure

Tokens are stored in Firestore with the following structure:

```json
{
  "user_id": "106251072616484621570",
  "access_token": "encrypted_token_data",
  "item_id": "unique_plaid_item_id",
  "institution_id": "ins_109508",
  "institution_name": "Chase Bank",
  "status": "active",
  "environment": "sandbox",
  "created_at": "2025-08-08T02:00:00Z",
  "updated_at": "2025-08-08T02:00:00Z",
  "last_used_at": "2025-08-08T01:30:00Z",
  "metadata": {
    "name": "Chase Bank",
    "url": "https://chase.com",
    "primary_color": "#117ACA"
  }
}
```

## Scheduled Tasks

### Daily Cleanup (2:00 AM)

- Removes expired and revoked tokens
- Identifies and marks invalid tokens
- Removes tokens not used in 90+ days
- Logs cleanup statistics

### Weekly Analytics (Sunday 1:00 AM)

- Generates comprehensive token analytics
- Logs token health metrics
- Tracks institution and user trends

## Security Features

### Token Encryption

- All access tokens are encrypted before storage
- Uses PBKDF2HMAC with SHA256 for key derivation
- Production-ready encryption implementation

### Authentication Requirements

- All management endpoints require valid JWT authentication
- User-specific operations are properly scoped
- System-wide operations require authenticated users

### Token Validation

- Real-time validation with Plaid API
- Automatic marking of invalid tokens
- Graceful handling of Plaid API errors

## Monitoring & Logging

### Log Levels

- `INFO`: Normal operations and statistics
- `WARNING`: Non-critical issues (e.g., invalid tokens found)
- `ERROR`: Critical failures requiring attention

### Key Metrics

- Token creation and usage rates
- Cleanup success/failure rates
- Institution distribution changes
- User activity patterns

## Configuration

### Environment Variables

- `TOKEN_ENCRYPTION_KEY`: Key for token encryption (production)
- `PLAID_CLIENT_ID`: Plaid client identifier
- `PLAID_SECRET`: Plaid API secret
- `PLAID_ENV`: Environment (sandbox/production)

### Cleanup Thresholds

- **Default Stale Threshold**: 90 days
- **Analytics Thresholds**: 30 and 90 days
- **Cleanup Schedule**: Daily at 2:00 AM
- **Analytics Schedule**: Weekly on Sunday at 1:00 AM

## Best Practices

### Development

```bash
# Test cleanup with shorter threshold
python manage_tokens.py cleanup --days 7

# Monitor analytics regularly
python manage_tokens.py analytics
```

### Production

- Monitor logs for cleanup failures
- Review weekly analytics reports
- Adjust stale thresholds based on usage patterns
- Set up alerts for high token failure rates

### User Management

- Revoke tokens when users delete accounts
- Clean up stale tokens before major updates
- Validate token health after Plaid API changes

## Troubleshooting

### Common Issues

**APScheduler Import Error**

```bash
pip install APScheduler>=3.10.4
```

**Firebase Connection Issues**

- Verify service account credentials
- Check Firestore security rules
- Ensure proper network connectivity

**Token Validation Failures**

- Check Plaid API status
- Verify client credentials
- Review token encryption/decryption

**High Stale Token Count**

- Review user activity patterns
- Consider adjusting thresholds
- Check for integration issues

### Debug Mode

Add detailed logging for troubleshooting:

```python
import logging
logging.getLogger('app.services.plaid_service').setLevel(logging.DEBUG)
```
