"""
Quick test: verify LinkedIn cookies are working.

Usage:
    python test_linkedin_setup.py

Reads cookies from .env file or prompts you to paste them.
"""

import sys
import os
import json


def get_cookie():
    """Get li_at cookie from .env or user input."""
    # Try .env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    li_at = None

    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("LINKEDIN_LI_AT_COOKIE="):
                    li_at = line.split("=", 1)[1].strip()
                    break

    if not li_at:
        print("No li_at cookie found in .env file.")
        print()
        li_at = input("Paste your li_at cookie value here: ").strip()

    if not li_at:
        print("[FAIL] No cookie provided")
        return None

    # Basic validation
    if len(li_at) < 50:
        print(f"[WARN] Cookie seems too short ({len(li_at)} chars). A real li_at cookie is usually 200+ characters.")
    else:
        print(f"[OK]   Cookie length: {len(li_at)} characters (looks right)")

    return li_at


def test_linkedin_access(li_at):
    """Test if the cookie gives us access to LinkedIn."""
    try:
        import httpx
    except ImportError:
        print("[FAIL] httpx not installed. Run: pip install httpx")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"li_at={li_at}",
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "x-li-lang": "en_US",
        "x-restli-protocol-version": "2.0.0",
    }

    # Test: fetch own profile
    url = "https://www.linkedin.com/voyager/api/me"

    print(f"Testing LinkedIn API access...")
    try:
        with httpx.Client(follow_redirects=True, timeout=15) as client:
            response = client.get(url, headers=headers)

        if response.status_code == 200:
            print(f"[OK]   LinkedIn API responded with 200")
            try:
                data = response.json()
                name = data.get("plainId") or data.get("publicIdentifier") or "unknown"
                print(f"[OK]   Logged in as: {name}")
            except Exception:
                print(f"[OK]   Got a valid response (couldn't parse profile name)")
            print()
            print("  >>> LinkedIn cookies are WORKING! <<<")

        elif response.status_code == 401:
            print(f"[FAIL] Got 401 Unauthorized")
            print("       Your li_at cookie is expired or invalid.")
            print("       Log into LinkedIn again and get a fresh cookie.")

        elif response.status_code == 403:
            print(f"[FAIL] Got 403 Forbidden")
            print("       LinkedIn is blocking this request. Try:")
            print("       1. Get fresh cookies from your browser")
            print("       2. Make sure you're logged into linkedin.com in your browser")

        else:
            print(f"[WARN] Got status code: {response.status_code}")
            print(f"       Response: {response.text[:200]}")

    except httpx.ConnectError:
        print(f"[FAIL] Could not connect to LinkedIn. Check your internet connection.")
    except Exception as e:
        print(f"[FAIL] Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("  LinkedIn Cookie Checker")
    print("=" * 60)
    print()

    li_at = get_cookie()
    if li_at:
        test_linkedin_access(li_at)
