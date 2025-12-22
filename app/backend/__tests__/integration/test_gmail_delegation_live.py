#!/usr/bin/env python3
"""Live Gmail API tests with domain-wide delegation.

Tests the service account's ability to impersonate workspace users
via domain-wide delegation (JWT bearer token flow).
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.integrations.gmail.client import GmailClient


class GmailDelegationLiveTestRunner:
    """Live test runner for Gmail domain-wide delegation."""

    def __init__(self):
        """Initialize test runner."""
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {"passed": 0, "failed": 0, "total": 0},
            "delegation_tests": {},
            "errors": [],
        }
        self.client: GmailClient | None = None
        self.credentials: dict = {}

    def load_credentials(self) -> bool:
        """Load service account credentials from .env.

        Returns:
            True if credentials loaded successfully, False otherwise.
        """
        print("\n📋 LOADING CREDENTIALS")
        print("=" * 60)

        # Try multiple paths
        env_file = Path(__file__).parent.parent.parent.parent.parent / ".env"
        cred_paths = [
            Path("app/backend/config/credentials/google-service-account.json"),
            Path("/Users/yasmineseidu/Desktop/Coding/yasmines-team")
            / "app/backend/config/credentials/google-service-account.json",
        ]

        credentials_file = None
        for path in cred_paths:
            if path.exists():
                credentials_file = path
                break

        if not credentials_file:
            print(f"❌ Credentials file not found in any of:")
            for path in cred_paths:
                print(f"   - {path}")
            return False

        try:
            with open(credentials_file) as f:
                self.credentials = json.load(f)

            print(f"✅ Credentials loaded successfully")
            print(f"   Type: {self.credentials.get('type')}")
            print(f"   Project: {self.credentials.get('project_id')}")
            print(f"   Email: {self.credentials.get('client_email')}")

            return True

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse credentials JSON: {e}")
            self.test_results["errors"].append(f"JSON parse error: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to load credentials: {e}")
            self.test_results["errors"].append(f"Load error: {e}")
            return False

    async def test_delegation_to_user(self, user_email: str) -> bool:
        """Test delegation to a specific workspace user.

        Args:
            user_email: Workspace email to impersonate (e.g., yasmine@smarterteam.ai)

        Returns:
            True if delegation test passed, False otherwise.
        """
        print(f"\n▶️  Testing delegation to: {user_email}")

        try:
            # Create client with delegation
            self.client = GmailClient(
                credentials_json=self.credentials, user_email=user_email
            )

            # Authenticate (this will use domain-wide delegation)
            await self.client.authenticate()
            print(f"   ✅ Authentication successful with delegation")

            # Test 1: Get user profile
            print(f"   📧 Getting user profile...")
            profile = await self.client.get_user_profile()

            if not profile:
                print(f"   ❌ Failed to get user profile")
                return False

            print(f"   ✅ Profile retrieved:")
            print(f"      Email: {profile.get('emailAddress', 'N/A')}")
            print(f"      Messages: {profile.get('messagesTotal', 0)}")
            print(f"      Threads: {profile.get('threadsTotal', 0)}")

            # Test 2: List messages
            print(f"   📬 Listing messages...")
            messages = await self.client.list_messages(max_results=5)
            print(f"   ✅ Listed {len(messages)} messages")

            # Test 3: Get labels
            print(f"   🏷️  Getting labels...")
            labels = await self.client.get_labels()
            print(f"   ✅ Found {len(labels)} labels")

            await self.client.close()
            return True

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Delegation test failed: {error_msg}")

            # Check for specific errors
            if "not found" in error_msg.lower():
                print(f"   💡 Hint: User '{user_email}' may not exist in workspace")
            elif "insufficient permissions" in error_msg.lower():
                print(f"   💡 Hint: Service account may lack necessary scopes")
            elif "invalid" in error_msg.lower():
                print(f"   💡 Hint: Email format or delegation setup may be invalid")

            self.test_results["errors"].append(
                f"Delegation test failed for {user_email}: {error_msg}"
            )

            if self.client:
                await self.client.close()
            return False

    async def test_delegation_features(self) -> bool:
        """Test specific delegation features.

        Returns:
            True if all features work, False otherwise.
        """
        user_email = "yasmine@smarterteam.ai"  # Primary workspace user
        print(f"\n▶️  Testing delegation features for: {user_email}")

        try:
            # Create client with delegation
            self.client = GmailClient(
                credentials_json=self.credentials, user_email=user_email
            )

            # Authenticate
            await self.client.authenticate()
            print(f"   ✅ Authenticated with delegation")

            # Feature 1: Get raw message
            print(f"   📬 Testing message retrieval...")
            messages = await self.client.list_messages(max_results=1)

            if messages:
                msg_id = messages[0]["id"]
                message = await self.client.get_message(msg_id)
                if message:
                    print(f"   ✅ Retrieved message: {msg_id[:20]}...")
                else:
                    print(f"   ⚠️  Message retrieval returned empty")

            # Feature 2: Get label
            print(f"   🏷️  Testing label retrieval...")
            labels = await self.client.get_labels()
            if labels:
                label_id = labels[0].get("id")
                label = await self.client.get_label(label_id)
                if label:
                    print(f"   ✅ Retrieved label: {label.get('name', 'N/A')}")

            # Feature 3: Draft operations
            print(f"   📝 Testing draft operations...")
            drafts = await self.client.list_drafts(max_results=1)
            print(f"   ✅ Listed {len(drafts)} drafts")

            # Feature 4: Thread operations
            print(f"   🧵 Testing thread operations...")
            threads = await self.client.list_threads(max_results=1)
            print(f"   ✅ Listed {len(threads)} threads")

            await self.client.close()
            return True

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Feature test failed: {error_msg}")
            self.test_results["errors"].append(f"Feature test failed: {error_msg}")

            if self.client:
                await self.client.close()
            return False

    async def test_multiple_delegations(self) -> bool:
        """Test delegation to multiple users.

        Returns:
            True if all delegations work, False otherwise.
        """
        test_users = [
            "yasmine@smarterteam.ai",  # Primary user
            # Add more workspace users here as needed
        ]

        print(f"\n🔄 TESTING MULTIPLE DELEGATIONS")
        print("=" * 60)

        success_count = 0

        for user_email in test_users:
            passed = await self.test_delegation_to_user(user_email)

            self.test_results["delegation_tests"][user_email] = (
                "✅ PASSED" if passed else "❌ FAILED"
            )

            if passed:
                success_count += 1
                self.test_results["summary"]["passed"] += 1
            else:
                self.test_results["summary"]["failed"] += 1

            self.test_results["summary"]["total"] += 1

        return success_count == len(test_users)

    async def run_all_tests(self) -> bool:
        """Run all delegation tests.

        Returns:
            True if all tests pass, False otherwise.
        """
        print("\n" + "=" * 60)
        print("🧪 GMAIL DOMAIN-WIDE DELEGATION LIVE TESTS")
        print("=" * 60)

        # Load credentials
        if not self.load_credentials():
            print("\n❌ Failed to load credentials")
            return False

        # Run tests
        try:
            # Test 1: Multiple user delegations
            delegations_passed = await self.test_multiple_delegations()

            # Test 2: Delegation features
            print("\n" + "=" * 60)
            features_passed = await self.test_delegation_features()

            # Print summary
            print("\n" + "=" * 60)
            print("📊 TEST SUMMARY")
            print("=" * 60)

            total = self.test_results["summary"]["total"]
            passed = self.test_results["summary"]["passed"]
            failed = self.test_results["summary"]["failed"]

            print(f"\n📈 RESULTS")
            print(f"   Passed: {passed}/{total}")
            print(f"   Failed: {failed}/{total}")

            if total > 0:
                success_rate = (passed / total) * 100
                print(f"   Success Rate: {success_rate:.1f}%")

            if self.test_results["errors"]:
                print(f"\n⚠️  ERRORS ({len(self.test_results['errors'])})")
                for error in self.test_results["errors"]:
                    print(f"   - {error}")

            # Save report
            report_path = Path(__file__).parent / "DELEGATION_TEST_REPORT.json"
            with open(report_path, "w") as f:
                json.dump(self.test_results, f, indent=2, default=str)

            print(f"\n📄 Report saved to: {report_path}")

            # Final status
            print("\n" + "=" * 60)
            if failed == 0 and passed > 0:
                print("✅ ALL DELEGATION TESTS PASSED!")
            else:
                print(f"❌ {failed} DELEGATION TESTS FAILED")

            print("=" * 60)

            return delegations_passed and features_passed

        except Exception as e:
            print(f"\n❌ Unexpected error during tests: {e}")
            self.test_results["errors"].append(f"Unexpected error: {e}")
            return False


async def main() -> None:
    """Run all tests."""
    runner = GmailDelegationLiveTestRunner()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
