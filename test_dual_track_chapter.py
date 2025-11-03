#!/usr/bin/env python3
"""
End-to-end test: Create a chapter and verify dual-track research
"""

import asyncio
import httpx
import sys
import time
from datetime import datetime


API_URL = "http://localhost:8002"
TEST_EMAIL = "dualtrack@test.com"
TEST_PASSWORD = "Test123456"  # Test user password


async def login():
    """Login and get JWT token"""
    print("=" * 60)
    print("STEP 1: Authentication")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Try to login
            response = await client.post(
                f"{API_URL}/api/v1/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                print(f"✓ Logged in as {TEST_EMAIL}")
                return token
            else:
                print(f"✗ Login failed: {response.status_code}")
                print(f"  Response: {response.text}")

                # Try to register
                print(f"\nTrying to register user...")
                reg_response = await client.post(
                    f"{API_URL}/api/v1/auth/register",
                    json={
                        "email": TEST_EMAIL,
                        "password": TEST_PASSWORD,
                        "full_name": "Test User"
                    }
                )

                if reg_response.status_code == 201:
                    print(f"✓ Registered new user")
                    # Login again
                    login_response = await client.post(
                        f"{API_URL}/api/v1/auth/login",
                        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
                    )
                    if login_response.status_code == 200:
                        token = login_response.json().get("access_token")
                        print(f"✓ Logged in successfully")
                        return token

                return None

        except Exception as e:
            print(f"✗ Authentication error: {str(e)}")
            return None


async def create_chapter(token):
    """Create a new chapter"""
    print("\n" + "=" * 60)
    print("STEP 2: Create Chapter with Dual-Track Research")
    print("=" * 60)

    chapter_data = {
        "topic": "Craniopharyngioma Surgical Management",
        "chapter_type": "surgical_disease"
    }

    print(f"Creating chapter: '{chapter_data['topic']}'")
    print(f"Type: {chapter_data['chapter_type']}")

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{API_URL}/api/v1/chapters",
                json=chapter_data,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 201:
                chapter = response.json()
                chapter_id = chapter.get("id")
                print(f"✓ Chapter created successfully")
                print(f"  ID: {chapter_id}")
                print(f"  Status: {chapter.get('generation_status')}")
                return chapter_id
            else:
                print(f"✗ Chapter creation failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

        except Exception as e:
            print(f"✗ Chapter creation error: {str(e)}")
            return None


async def monitor_chapter_progress(token, chapter_id, max_wait=300):
    """Monitor chapter generation progress"""
    print("\n" + "=" * 60)
    print("STEP 3: Monitor Chapter Generation Progress")
    print("=" * 60)
    print(f"Monitoring chapter: {chapter_id}")
    print(f"Check logs with: docker logs neurocore-api -f")
    print()

    start_time = time.time()
    last_status = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while time.time() - start_time < max_wait:
            try:
                response = await client.get(
                    f"{API_URL}/api/v1/chapters/{chapter_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code == 200:
                    chapter = response.json()
                    status = chapter.get("generation_status")

                    if status != last_status:
                        elapsed = time.time() - start_time
                        print(f"[{elapsed:5.1f}s] Status: {status}")
                        last_status = status

                        # Show Stage 4 details when external research completes
                        if status in ["stage_5_planning", "stage_6_generation", "completed"]:
                            stage_4 = chapter.get("stage_4_external_research", {})
                            if stage_4:
                                print("\n" + "-" * 60)
                                print("STAGE 4: External Research Results")
                                print("-" * 60)

                                # Check for dual-track structure
                                research_methods = stage_4.get("research_methods", [])
                                sources_by_type = stage_4.get("sources_by_type", {})
                                parallel_exec = stage_4.get("parallel_execution", False)

                                print(f"Research Methods: {research_methods}")
                                print(f"Parallel Execution: {parallel_exec}")
                                print(f"Sources by Type: {sources_by_type}")
                                print()

                                # Count sources
                                pubmed_sources = stage_4.get("pubmed_sources", [])
                                ai_sources = stage_4.get("ai_researched_sources", [])
                                all_sources = stage_4.get("sources", [])

                                print(f"✓ Total Sources: {len(all_sources)}")
                                print(f"  - PubMed: {len(pubmed_sources)}")
                                print(f"  - AI Research: {len(ai_sources)}")

                                # Show first AI source
                                if ai_sources:
                                    print(f"\nFirst AI-Researched Source:")
                                    ai_src = ai_sources[0]
                                    print(f"  Title: {ai_src.get('title', 'N/A')[:60]}...")
                                    print(f"  Source Type: {ai_src.get('source_type')}")
                                    print(f"  Research Method: {ai_src.get('research_method')}")

                                print("-" * 60 + "\n")

                    if status == "completed":
                        print(f"\n✓ Chapter generation completed!")
                        return True
                    elif status == "failed":
                        print(f"\n✗ Chapter generation failed")
                        error = chapter.get("error_message")
                        if error:
                            print(f"  Error: {error}")
                        return False

                await asyncio.sleep(5)

            except Exception as e:
                print(f"✗ Monitoring error: {str(e)}")
                await asyncio.sleep(5)

    print(f"\n⚠ Timeout after {max_wait}s")
    return False


async def verify_dual_track_structure(token, chapter_id):
    """Verify the dual-track structure in the generated chapter"""
    print("\n" + "=" * 60)
    print("STEP 4: Verify Dual-Track Structure")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_URL}/api/v1/chapters/{chapter_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code != 200:
            print(f"✗ Failed to fetch chapter")
            return False

        chapter = response.json()
        stage_4 = chapter.get("stage_4_external_research", {})

        # Check dual-track structure
        checks = {
            "research_methods exists": "research_methods" in stage_4,
            "sources_by_type exists": "sources_by_type" in stage_4,
            "pubmed_sources exists": "pubmed_sources" in stage_4,
            "ai_researched_sources exists": "ai_researched_sources" in stage_4,
            "parallel_execution flag": "parallel_execution" in stage_4,
        }

        print("\nStructure Checks:")
        all_passed = True
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            if not passed:
                all_passed = False

        # Check citations
        references = chapter.get("references", [])
        if references:
            print(f"\n✓ References: {len(references)} total")

            # Check for source_type in references
            has_source_type = any("source_type" in ref for ref in references)
            print(f"  {'✓' if has_source_type else '✗'} Source type metadata preserved")

        return all_passed


async def main():
    """Run full end-to-end test"""
    print("\n" + "=" * 80)
    print(" " * 20 + "DUAL-TRACK RESEARCH E2E TEST")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {API_URL}")
    print()

    # Step 1: Login
    token = await login()
    if not token:
        print("\n❌ TEST FAILED: Authentication failed")
        return False

    # Step 2: Create chapter
    chapter_id = await create_chapter(token)
    if not chapter_id:
        print("\n❌ TEST FAILED: Chapter creation failed")
        return False

    # Step 3: Monitor progress
    success = await monitor_chapter_progress(token, chapter_id, max_wait=600)
    if not success:
        print("\n❌ TEST FAILED: Chapter generation did not complete")
        return False

    # Step 4: Verify structure
    structure_ok = await verify_dual_track_structure(token, chapter_id)

    print("\n" + "=" * 80)
    if structure_ok:
        print("✅ ALL TESTS PASSED - DUAL-TRACK RESEARCH WORKING!")
        print(f"   Chapter ID: {chapter_id}")
        print(f"   View at: http://localhost:3002/chapters/{chapter_id}")
    else:
        print("⚠️  TESTS PARTIALLY PASSED - See structure checks above")
    print("=" * 80)
    print()

    return structure_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
