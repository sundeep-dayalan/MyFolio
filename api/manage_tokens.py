#!/usr/bin/env python3
"""
Token lifecycle management CLI script.
Usage: python manage_tokens.py [command] [options]
"""

import sys
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.plaid_service import PlaidService
from app.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def cleanup_tokens(days_threshold: int = 90):
    """Run token cleanup manually."""
    try:
        plaid_service = PlaidService()
        stats = plaid_service.cleanup_expired_tokens(days_threshold)

        print("🧹 Token Cleanup Results:")
        print(f"   Total tokens checked: {stats['total_checked']}")
        print(f"   Expired tokens removed: {stats['expired_removed']}")
        print(f"   Stale tokens removed: {stats['stale_removed']}")
        print(f"   Invalid tokens marked: {stats['invalid_marked']}")
        print(f"   Revoked tokens removed: {stats['revoked_removed']}")
        print(f"   Total cleaned: {stats['total_cleaned']}")

        return stats

    except Exception as e:
        print(f"❌ Token cleanup failed: {e}")
        logger.error(f"Token cleanup failed: {e}")
        return None


def get_analytics():
    """Get token analytics."""
    try:
        plaid_service = PlaidService()
        analytics = plaid_service.get_token_analytics()

        print("📊 Token Analytics:")
        print(f"   Total tokens: {analytics['total_tokens']}")
        print(f"   Active tokens: {analytics['active_tokens']}")
        print(f"   Expired tokens: {analytics['expired_tokens']}")
        print(f"   Revoked tokens: {analytics['revoked_tokens']}")
        print(f"   Unique users: {analytics['unique_users']}")
        print(f"   Stale tokens (30 days): {analytics['stale_tokens_30_days']}")
        print(f"   Stale tokens (90 days): {analytics['stale_tokens_90_days']}")

        print("\n🏦 Institutions:")
        for institution, count in analytics["institutions"].items():
            print(f"   {institution}: {count}")

        print("\n🌍 Environments:")
        for env, count in analytics["environments"].items():
            print(f"   {env}: {count}")

        return analytics

    except Exception as e:
        print(f"❌ Analytics generation failed: {e}")
        logger.error(f"Analytics generation failed: {e}")
        return None


def revoke_user_tokens(user_id: str):
    """Revoke all tokens for a specific user."""
    try:
        plaid_service = PlaidService()
        count = plaid_service.revoke_all_user_tokens(user_id)

        print(f"🔐 Revoked {count} tokens for user {user_id}")
        return count

    except Exception as e:
        print(f"❌ Token revocation failed: {e}")
        logger.error(f"Token revocation failed: {e}")
        return 0


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Token lifecycle management for Personal Wealth Management API"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Clean up expired and stale tokens"
    )
    cleanup_parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Days threshold for stale tokens (default: 90)",
    )

    # Analytics command
    subparsers.add_parser("analytics", help="Show token analytics")

    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke all tokens for a user")
    revoke_parser.add_argument("user_id", help="User ID to revoke tokens for")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    print("🚀 Personal Wealth Management - Token Management")
    print("=" * 50)

    if args.command == "cleanup":
        cleanup_tokens(args.days)
    elif args.command == "analytics":
        get_analytics()
    elif args.command == "revoke":
        revoke_user_tokens(args.user_id)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main()
