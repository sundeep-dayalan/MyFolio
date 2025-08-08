#!/usr/bin/env python3
"""
Test script to simulate the complete Plaid integration flow
"""

import requests
import json

API_BASE = "http://localhost:8000/api/v1"
USER_ID = "dev-user-123"

def test_plaid_flow():
    print("🔍 Testing Plaid Integration Flow")
    print("=" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "X-Dev-User-ID": USER_ID
    }
    
    # Step 1: Test connection
    print("\n1. Testing Plaid connection...")
    response = requests.get(f"{API_BASE}/plaid/test")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Step 2: Create link token
    print("\n2. Creating link token...")
    response = requests.post(f"{API_BASE}/plaid/create_link_token", headers=headers)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Link token: {data.get('link_token', 'None')[:20]}...")
    
    # Step 3: Check current accounts (should be empty)
    print("\n3. Checking current accounts...")
    response = requests.get(f"{API_BASE}/plaid/accounts", headers=headers)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Accounts: {len(data.get('accounts', []))}")
    print(f"   Balance: ${data.get('total_balance', 0)}")
    
    print("\n" + "=" * 50)
    print("✅ Basic flow test completed!")
    print("\n📝 Next steps to test with Plaid sandbox:")
    print("   1. Use the frontend to trigger Plaid Link")
    print("   2. In the Plaid sandbox, use these test credentials:")
    print("      - Username: user_good")
    print("      - Password: pass_good")
    print("   3. Select accounts to connect")
    print("   4. Check the console logs for debugging")

if __name__ == "__main__":
    test_plaid_flow()
