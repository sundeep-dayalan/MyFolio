# Testing Your Secure Google OAuth Flow 🧪

## Current Setup Status ✅
- ✅ FastAPI server running on `http://localhost:8002`
- ✅ Google OAuth endpoints configured and working
- ✅ Client ID and Client Secret properly set
- ✅ Redirect URI correctly configured
- ✅ Updated LoginPage.tsx for secure OAuth
- ✅ OAuth callback page created

## Testing Methods

### Method 1: Quick Browser Test (Recommended)

1. **Start your React development server:**
   ```bash
   cd /Users/sundeepdayalan/Developer/React\ Projects/personal-wealth-management/react-app
   npm start
   # or
   npm run dev
   ```

2. **Open your browser and navigate to:**
   ```
   http://localhost:3000/login
   # or whatever port your React app uses
   ```

3. **You should see:**
   - A "Continue with Google" button
   - A green "✓ OAuth Ready" indicator
   - The button should be enabled (not grayed out)

4. **Click "Continue with Google":**
   - You'll be redirected to Google's consent screen
   - Log in with your Google account
   - Grant permissions to your app
   - You'll be redirected back to your callback URL

### Method 2: Direct API Testing

Test the OAuth flow step by step:

1. **Test OAuth Status:**
   ```bash
   curl "http://localhost:8002/api/v1/auth/oauth/status"
   ```
   Expected: `{"google_oauth_enabled":true,"redirect_uri":"http://localhost:8002/api/v1/auth/oauth/google/callback","available_flows":["authorization_code"]}`

2. **Test OAuth Initiation:**
   ```bash
   curl -v "http://localhost:8002/api/v1/auth/oauth/google"
   ```
   Expected: `302 redirect` to Google's OAuth server with proper parameters

3. **Open the redirect URL in browser:**
   - Copy the `location` header from the curl response
   - Paste it into your browser
   - Complete the Google OAuth flow

### Method 3: Direct URL Testing

1. **Open in browser:**
   ```
   http://localhost:8002/api/v1/auth/oauth/google
   ```
   This will immediately redirect you to Google's OAuth consent screen.

## What to Expect During Testing

### Step 1: OAuth Initiation
- **URL**: `http://localhost:8002/api/v1/auth/oauth/google`
- **Expected**: Redirect to `https://accounts.google.com/o/oauth2/auth?...`
- **Signs of Success**: 
  - Browser redirects to Google
  - URL contains your client_id
  - State parameter is present

### Step 2: Google Consent Screen
- **What you'll see**: Google's permission request screen
- **Required actions**: 
  - Log in with your Google account
  - Review and accept permissions (email, profile, openid)
- **Signs of Success**: Google shows your app name and requested permissions

### Step 3: Callback Processing
- **URL**: `http://localhost:8002/api/v1/auth/oauth/google/callback?code=...&state=...`
- **Expected**: JSON response with user data and token
- **Example Response**:
  ```json
  {
    "user": {
      "id": "google_user_id",
      "email": "your.email@gmail.com",
      "name": "Your Name",
      "picture": "https://...",
      "is_active": true,
      "created_at": "2025-08-03T21:15:00Z",
      "updated_at": "2025-08-03T21:15:00Z"
    },
    "token": {
      "access_token": "eyJ...",
      "token_type": "bearer",
      "expires_in": 1800
    },
    "message": "Authentication successful"
  }
  ```

## Adding Route Configuration

To complete the React testing, you need to add the OAuth callback route to your React Router configuration:

```typescript
// In your main App.tsx or router configuration
import OAuthCallbackPage from './pages/OAuthCallbackPage';

// Add this route:
<Route path="/auth/callback" element={<OAuthCallbackPage />} />
```

## Troubleshooting Common Issues

### 1. "OAuth is not configured" Error
- **Cause**: Missing or incorrect environment variables
- **Fix**: Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`

### 2. "Invalid redirect URI" Error
- **Cause**: Redirect URI mismatch in Google Console
- **Fix**: In Google Cloud Console, add `http://localhost:8002/api/v1/auth/oauth/google/callback` to authorized redirect URIs

### 3. "Invalid client" Error
- **Cause**: Wrong client ID or client secret
- **Fix**: Verify credentials in Google Cloud Console

### 4. CORS Errors
- **Cause**: Frontend and backend on different ports
- **Fix**: CORS is already configured in your FastAPI app for localhost

### 5. State Mismatch Error
- **Cause**: Session cookie issues
- **Fix**: Ensure cookies are enabled and session middleware is working

## Security Testing

### Test CSRF Protection:
```bash
# This should fail with "Invalid state parameter"
curl "http://localhost:8002/api/v1/auth/oauth/google/callback?code=fake&state=wrong"
```

### Test Missing Parameters:
```bash
# This should fail with "Authorization code is required"
curl "http://localhost:8002/api/v1/auth/oauth/google/callback"
```

## Production Considerations

Before deploying:

1. **Update redirect URIs** in Google Console for your production domain
2. **Use HTTPS** for all OAuth flows in production
3. **Update CORS settings** for your production frontend domain
4. **Use secure session cookies** with proper flags
5. **Implement proper error logging** and monitoring

## Quick Test Commands

```bash
# 1. Check API is running
curl http://localhost:8002/health

# 2. Check OAuth status
curl http://localhost:8002/api/v1/auth/oauth/status

# 3. Start OAuth flow (will redirect)
curl -v http://localhost:8002/api/v1/auth/oauth/google

# 4. Test in browser
open http://localhost:8002/api/v1/auth/oauth/google
```

## Expected Success Flow

1. **LoginPage** → Shows "Continue with Google" button
2. **Click button** → Redirects to `http://localhost:8002/api/v1/auth/oauth/google`
3. **Server redirect** → Takes you to Google's OAuth consent screen
4. **Google login** → User grants permissions
5. **Google callback** → Redirects to `http://localhost:8002/api/v1/auth/oauth/google/callback?code=...`
6. **Server processing** → Exchanges code for tokens, creates/finds user
7. **Response** → Returns user data and JWT token
8. **Frontend** → Stores token and redirects to dashboard

Your OAuth flow is now ready for testing! 🚀
