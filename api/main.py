import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, HTTPException, Request, Query
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import httpx
import json
import os
from datetime import datetime
import urllib.parse
from dotenv import load_dotenv
import jwt

# Load environment variables
load_dotenv()

# --- Configuration ---
SERVICE_ACCOUNT_KEY_PATH = 'service-account.json'
# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://your-frontend-domain.com")
API_URL = os.getenv("API_URL", "https://your-api-domain.com")

# --- FastAPI App Initialization ---
app = FastAPI(title="MyFolio API", version="1.0.0")

# Get allowed origins from environment
allowed_origins = os.getenv("ALLOWED_ORIGINS", FRONTEND_URL).split(",")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth state management
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Global variable to hold the Firestore client
db = None

@app.on_event("startup")
async def startup_event():
    """
    Initializes Firebase Admin SDK when the FastAPI application starts up.
    """
    global db
    try:
        # Load the service account credentials
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)

        # Initialize the Firebase Admin SDK
        firebase_admin.initialize_app(cred, {
            'projectId': 'fit-guide-465001-p3'
        })
        print("Firebase Admin SDK initialized successfully!")

        # Get a Firestore client instance for your SPECIFIC NAMED DATABASE
        # This parameter *should* be available after the upgrade
        db = firestore.client(database_id="personal-wealth-management")
        print("Firestore client obtained for 'personal-wealth-management'!")

    except Exception as e:
        print(f"Error initializing Firebase or Firestore: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize Firebase services.")


@app.get("/")
async def read_root():
    return {"message": "Welcome to your Firebase-connected FastAPI app!"}

@app.get("/users/{user_id}")
async def get_user_data(user_id: str):
    """
    Example endpoint to retrieve a user document from Firestore.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Firestore client not initialized.")

    doc_ref = db.collection('users').document(user_id)
    doc = doc_ref.get()

    if doc.exists:
        return {"user_id": user_id, "data": doc.to_dict()}
    else:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")

@app.post("/users")
async def create_user_data(user: dict):
    """
    Example endpoint to add or update a user document in Firestore.
    Expects a JSON body like: {"id": "some_id", "name": "John Doe", "email": "john@example.com"}
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Firestore client not initialized.")

    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required.")

    try:
        # Set a document with a specific ID
        doc_ref = db.collection('users').document(user_id)
        doc_ref.set(user) # This will create or overwrite the document

        return {"message": f"User '{user_id}' created/updated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing user data: {e}")

# Simple OAuth endpoints for testing
@app.get("/api/v1/auth/oauth/google")
async def google_oauth_initiate(request: Request):
    """Initiate Google OAuth flow."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # Generate state for CSRF protection
    state = os.urandom(32).hex()
    request.session["oauth_state"] = state
    
    # Build Google OAuth URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{API_URL}/api/v1/auth/oauth/google/callback",
        "scope": "openid email profile",
        "response_type": "code",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)

@app.get("/api/v1/auth/oauth/google/callback")
async def google_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None)
):
    """Handle Google OAuth callback."""
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?success=false&error={error}")
    
    # Verify state for CSRF protection
    session_state = request.session.get("oauth_state")
    if not session_state or session_state != state:
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?success=false&error=Invalid%20state")
    
    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": f"{API_URL}/api/v1/auth/oauth/google/callback"
                }
            )
            
            if token_response.status_code != 200:
                return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?success=false&error=Token%20exchange%20failed")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            if not access_token:
                return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?success=false&error=No%20access%20token")
            
            # Get user info from Google
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?success=false&error=Failed%20to%20get%20user%20info")
            
            user_info = user_response.json()
            
            # Create a mock user session (since Firestore might be disabled)
            user_data = {
                "id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "given_name": user_info.get("given_name"),
                "family_name": user_info.get("family_name"),
                "picture": user_info.get("picture"),
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Store user in session for simplicity
            request.session["user"] = user_data
            request.session["access_token"] = access_token
            
            # Create a simple JWT token for the frontend
            import jwt
            token_payload = {
                "sub": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "type": "access_token",
                "auth_method": "google_oauth",
                "exp": int(datetime.utcnow().timestamp()) + 1800  # 30 minutes
            }
            token = jwt.encode(token_payload, "your-secret-key-here", algorithm="HS256")
            
            # URL encode the user data
            user_data_encoded = urllib.parse.quote(json.dumps(user_data))
            
            # Clean redirect without hash fragments
            redirect_url = f"{FRONTEND_URL}/auth/callback?success=true&token={token}&user={user_data_encoded}"
            
            return RedirectResponse(url=redirect_url)
            
            
    except Exception as e:
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?success=false&error=OAuth%20authentication%20failed")

@app.get("/api/v1/auth/oauth/status")
async def oauth_status(request: Request):
    """Get current OAuth authentication status."""
    user = request.session.get("user")
    if user:
        return {"authenticated": True, "user": user, "google_oauth_enabled": True}
    return {"authenticated": False, "google_oauth_enabled": True}

# To run this FastAPI app:
# 1. Save the code above as, for example, 'main.py'.
# 2. Make sure your 'serviceAccountKey.json' is in the specified path.
# 3. Run from your terminal: uvicorn main:app --reload
