#!/usr/bin/env python3
"""
Test script to verify data cleanup when unlinking banks.
"""

import requests
import json

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
USER_TOKEN = "your_test_user_token_here"  # You'll need to get this from your auth


def test_data_cleanup():
    """Test that account data is properly cleaned up when unlinking banks."""

    print("🧪 Testing Data Cleanup Lifecycle")
    print("=" * 50)

    headers = {
        "Authorization": f"Bearer {USER_TOKEN}",
        "Content-Type": "application/json",
    }

    # 1. Check current accounts
    print("\n1. Checking current accounts...")
    response = requests.get(f"{API_BASE_URL}/plaid/accounts", headers=headers)
    if response.status_code == 200:
        accounts_data = response.json()
        print(f"   ✅ Found {accounts_data.get('account_count', 0)} accounts")
        print(f"   💰 Total balance: ${accounts_data.get('total_balance', 0):,.2f}")
    else:
        print(f"   ❌ Failed to get accounts: {response.status_code}")
        return

    # 2. Check current items
    print("\n2. Checking current connected items...")
    response = requests.get(f"{API_BASE_URL}/plaid/items", headers=headers)
    if response.status_code == 200:
        items_data = response.json()
        items = items_data.get("items", [])
        print(f"   ✅ Found {len(items)} connected banks")
        for item in items:
            print(
                f"      🏦 {item.get('institution_name')} (ID: {item.get('item_id')})"
            )
    else:
        print(f"   ❌ Failed to get items: {response.status_code}")
        return

    if not items:
        print("   ⚠️  No banks connected - cannot test unlink functionality")
        return

    # 3. Test unlinking a single bank (if multiple exist)
    if len(items) > 1:
        print("\n3. Testing single bank unlink...")
        test_item = items[0]
        print(f"   🎯 Unlinking: {test_item.get('institution_name')}")

        response = requests.delete(
            f"{API_BASE_URL}/plaid/tokens/revoke/{test_item.get('item_id')}",
            headers=headers,
        )

        if response.status_code == 200:
            print("   ✅ Bank unlinked successfully")

            # Check if accounts were updated (should still have remaining banks)
            response = requests.get(f"{API_BASE_URL}/plaid/accounts", headers=headers)
            if response.status_code == 200:
                new_accounts_data = response.json()
                new_count = new_accounts_data.get("account_count", 0)
                original_count = accounts_data.get("account_count", 0)

                if new_count < original_count:
                    print(
                        f"   ✅ Account count reduced: {original_count} → {new_count}"
                    )
                else:
                    print(
                        f"   ⚠️  Account count unchanged: {new_count} (expected reduction)"
                    )
            else:
                print("   ❌ Failed to check accounts after unlink")
        else:
            print(f"   ❌ Failed to unlink bank: {response.status_code}")

    # 4. Test disconnect all
    print("\n4. Testing disconnect all...")
    response = requests.delete(
        f"{API_BASE_URL}/plaid/tokens/revoke-all", headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        revoked_count = result.get("revoked_count", 0)
        print(f"   ✅ Disconnected all banks: {revoked_count} tokens revoked")

        # Check if all account data was cleared
        response = requests.get(f"{API_BASE_URL}/plaid/accounts", headers=headers)
        if response.status_code == 200:
            final_accounts_data = response.json()
            final_count = final_accounts_data.get("account_count", 0)

            if final_count == 0:
                print("   ✅ All account data cleared successfully")
            else:
                print(f"   ❌ Account data not cleared: {final_count} accounts remain")
        else:
            print("   ⚠️  Could not verify account data clearance")
    else:
        print(f"   ❌ Failed to disconnect all: {response.status_code}")

    print("\n" + "=" * 50)
    print("🏁 Test completed!")


if __name__ == "__main__":
    print("⚠️  Note: You need to update USER_TOKEN with a valid auth token")
    print("   You can get this from your browser's dev tools when logged in")
    print()

    if USER_TOKEN == "your_test_user_token_here":
        print("❌ Please set a valid USER_TOKEN before running this test")
    else:
        test_data_cleanup()
