#!/usr/bin/env python3
"""
Startup diagnostic script to help debug Cloud Run deployment issues.
"""

import os
import sys
import traceback
from pathlib import Path

def check_environment():
    """Check critical environment variables."""
    print("=== Environment Variables Check ===")
    
    critical_vars = [
        "SECRET_KEY",
        "FIREBASE_PROJECT_ID", 
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "PLAID_CLIENT_ID",
        "PLAID_SECRET"
    ]
    
    missing_vars = []
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * 8} (set)")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    return missing_vars

def check_imports():
    """Check if critical imports work."""
    print("\n=== Import Check ===")
    
    try:
        import fastapi
        print(f"✅ FastAPI: {fastapi.__version__}")
    except Exception as e:
        print(f"❌ FastAPI import failed: {e}")
        return False
        
    try:
        import plaid
        print(f"✅ Plaid: {plaid.__version__}")
    except Exception as e:
        print(f"❌ Plaid import failed: {e}")
        return False
        
    try:
        import firebase_admin
        print(f"✅ Firebase Admin SDK available")
    except Exception as e:
        print(f"❌ Firebase Admin SDK import failed: {e}")
        return False
        
    return True

def check_app_creation():
    """Try to create the FastAPI app."""
    print("\n=== App Creation Check ===")
    
    try:
        # Add the app directory to Python path
        app_dir = Path(__file__).parent
        sys.path.insert(0, str(app_dir))
        
        from app.main import app
        print("✅ FastAPI app created successfully")
        return True
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic checks."""
    print("🔍 Starting Cloud Run Deployment Diagnostics\n")
    
    # Check environment
    missing_vars = check_environment()
    
    # Check imports
    imports_ok = check_imports()
    
    # Check app creation
    app_ok = check_app_creation()
    
    print("\n=== Summary ===")
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
    if not imports_ok:
        print("❌ Import issues detected")
    if not app_ok:
        print("❌ App creation failed")
        
    if not missing_vars and imports_ok and app_ok:
        print("✅ All checks passed! App should start successfully.")
        return 0
    else:
        print("❌ Issues detected. Check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
