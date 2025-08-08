#!/usr/bin/env python3
"""
Test script to simulate the Plaid token exchange process
This simulates what happens when a user successfully completes Plaid Link
"""

import requests
import json

API_BASE = "http://localhost:8000/api/v1"
USER_ID = "dev-user-123"

# This is a test public token from Plaid's documentation
# It's safe to use for testing and will be exchanged for a sandbox access token
TEST_PUBLIC_TOKEN = "public-sandbox-e6d8de7a-5af3-42ac-9f38-953b0d4fa17c"

def test_token_exchange():
    print("🔗 Testing Plaid Token Exchange")
    print("=" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "X-Dev-User-ID": USER_ID
    }
    
    # Test the exchange endpoint
    print("\n1. Attempting to exchange public token...")
    exchange_data = {"public_token": TEST_PUBLIC_TOKEN}
    
    response = requests.post(
        f"{API_BASE}/plaid/exchange_public_token", 
        headers=headers,
        json=exchange_data
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Success: {data.get('success', False)}")
        print(f"   Item ID: {data.get('item_id', 'None')}")
    else:
        print(f"   Error: {response.text}")
    
    # Now check if accounts are available
    print("\n2. Checking accounts after token exchange...")
    response = requests.get(f"{API_BASE}/plaid/accounts", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Accounts: {len(data.get('accounts', []))}")
        print(f"   Balance: ${data.get('total_balance', 0)}")
        
        if data.get('accounts'):
            print("\n   Account details:")
            for i, account in enumerate(data['accounts'][:3]):  # Show first 3
                print(f"     {i+1}. {account.get('name', 'Unknown')}")
                print(f"        Type: {account.get('type', 'Unknown')} - {account.get('subtype', 'Unknown')}")
                balance = account.get('balances', {}).get('current', 0) or 0
                print(f"        Balance: ${balance}")
    else:
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    test_token_exchange()
