#!/usr/bin/env python3
"""
Test Chapter Delete Functionality
Tests the DELETE /api/v1/chapters/{id} endpoint
"""

import requests
import sys

# Configuration
API_BASE = "http://localhost:8002/api/v1"
TEST_EMAIL = "test@neurocore.ai"  # Existing user from database
TEST_PASSWORD = "test123"  # Standard test password

def login():
    """Login and get access token"""
    print("🔐 Logging in...")
    # Send JSON for login
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Login successful!")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def get_chapters(token):
    """Get list of chapters"""
    print("\n📚 Fetching chapters...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/chapters", headers=headers)

    if response.status_code == 200:
        chapters = response.json()
        print(f"✅ Found {len(chapters)} chapters")
        return chapters
    else:
        print(f"❌ Failed to fetch chapters: {response.status_code}")
        print(f"   Response: {response.text}")
        return []

def delete_chapter(token, chapter_id):
    """Test deleting a chapter"""
    print(f"\n🗑️  Testing DELETE /chapters/{chapter_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(
        f"{API_BASE}/chapters/{chapter_id}",
        headers=headers
    )

    print(f"\n📊 Response Status: {response.status_code}")
    print(f"📄 Response Body: {response.text}")

    if response.status_code == 200:
        print(f"✅ Chapter deleted successfully!")
        return True
    else:
        print(f"❌ Delete failed!")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")

        # Try to parse error details
        try:
            error_data = response.json()
            if "detail" in error_data:
                print(f"   Error Detail: {error_data['detail']}")
        except:
            pass

        return False

def main():
    print("=" * 60)
    print("🔬 CHAPTER DELETE FUNCTIONALITY TEST")
    print("=" * 60)

    # Login
    token = login()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        sys.exit(1)

    # Get chapters
    chapters = get_chapters(token)
    if not chapters:
        print("\n⚠️  No chapters found to delete")
        return

    # Find a failed or old chapter to delete
    chapter_to_delete = None
    for chapter in chapters:
        if chapter.get("generation_status") == "failed":
            chapter_to_delete = chapter
            break

    if not chapter_to_delete and chapters:
        chapter_to_delete = chapters[-1]  # Use the last one

    if chapter_to_delete:
        print(f"\n📌 Selected chapter for deletion:")
        print(f"   ID: {chapter_to_delete['id']}")
        print(f"   Title: {chapter_to_delete['title']}")
        print(f"   Status: {chapter_to_delete['generation_status']}")

        # Attempt delete
        success = delete_chapter(token, chapter_to_delete["id"])

        if success:
            # Verify deletion
            print("\n🔍 Verifying deletion...")
            chapters_after = get_chapters(token)
            deleted_ids = [c["id"] for c in chapters_after]
            if chapter_to_delete["id"] not in deleted_ids:
                print("✅ Chapter successfully removed from database!")
            else:
                print("⚠️  Chapter still exists in database!")
    else:
        print("\n⚠️  No suitable chapter found for testing")

    print("\n" + "=" * 60)
    print("📊 TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
