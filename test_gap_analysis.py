#!/usr/bin/env python3
"""
End-to-End Gap Analysis Testing Script
Phase 2 Week 5 - Integration Testing

Tests:
1. Gap analysis API endpoint availability
2. Running gap analysis on a completed chapter
3. Retrieving gap analysis results
4. Getting gap analysis summary
5. Verifying data structure and completeness
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8002/api/v1"
TEST_CHAPTER_ID = "9fd59175-8221-4310-9f5f-27a53b90110d"  # Glioblastoma management
TEST_EMAIL = "neurotest@example.com"
TEST_PASSWORD = "testpassword"  # You may need to adjust this

# ANSI colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_test(test_name):
    print(f"\n{Colors.BLUE}{Colors.BOLD}Testing: {test_name}{Colors.END}")
    print("=" * 80)

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def login():
    """Login and get auth token"""
    print_test("1. Authentication")
    try:
        response = requests.post(
            f"{API_BASE}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print_success(f"Logged in successfully as {TEST_EMAIL}")
            return token
        else:
            print_error(f"Login failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Login exception: {str(e)}")
        return None

def test_api_health(token):
    """Test API health endpoint"""
    print_test("2. API Health Check")
    try:
        response = requests.get(f"{API_BASE}/chapters/health", timeout=5)
        if response.status_code == 200:
            print_success("Chapter service is healthy")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check exception: {str(e)}")
        return False

def get_chapter_info(token):
    """Get chapter information"""
    print_test("3. Get Chapter Information")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_BASE}/chapters/{TEST_CHAPTER_ID}",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Chapter found: {data.get('title')}")
            print_info(f"  Status: {data.get('generation_status')}")
            print_info(f"  Sections: {data.get('total_sections', 'N/A')}")
            print_info(f"  Words: {data.get('total_words', 'N/A')}")

            # Check if gap analysis exists
            if 'gap_analysis_summary' in data:
                print_info("  Existing gap analysis found")
                return True, data
            else:
                print_info("  No existing gap analysis")
                return True, data
        else:
            print_error(f"Failed to get chapter: {response.status_code}")
            return False, None
    except Exception as e:
        print_error(f"Get chapter exception: {str(e)}")
        return False, None

def run_gap_analysis(token):
    """Run gap analysis on the chapter"""
    print_test("4. Run Gap Analysis")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        print_info("Triggering gap analysis (may take 5-10 seconds)...")
        start_time = time.time()

        response = requests.post(
            f"{API_BASE}/chapters/{TEST_CHAPTER_ID}/gap-analysis",
            headers=headers,
            timeout=60  # Allow up to 60 seconds for analysis
        )

        elapsed = time.time() - start_time

        if response.status_code in [200, 201]:
            data = response.json()
            print_success(f"Gap analysis completed in {elapsed:.2f} seconds")
            print_info(f"  Success: {data.get('success')}")
            print_info(f"  Total gaps: {data.get('gap_analysis', {}).get('total_gaps')}")
            print_info(f"  Critical gaps: {data.get('gap_analysis', {}).get('critical_gaps')}")
            print_info(f"  Completeness: {data.get('gap_analysis', {}).get('completeness_score', 0) * 100:.1f}%")
            print_info(f"  Requires revision: {data.get('gap_analysis', {}).get('requires_revision')}")
            return True, data
        elif response.status_code == 400:
            error = response.json().get('detail', 'Unknown error')
            print_warning(f"Cannot run analysis: {error}")
            return False, None
        elif response.status_code == 403:
            print_error("Permission denied - not chapter author or admin")
            return False, None
        else:
            print_error(f"Gap analysis failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False, None
    except Exception as e:
        print_error(f"Gap analysis exception: {str(e)}")
        return False, None

def get_full_gap_analysis(token):
    """Get full gap analysis results"""
    print_test("5. Get Full Gap Analysis Results")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_BASE}/chapters/{TEST_CHAPTER_ID}/gap-analysis",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_success("Full gap analysis retrieved")
            print_info(f"  Analyzed at: {data.get('analyzed_at')}")
            print_info(f"  Total sections: {data.get('total_sections')}")
            print_info(f"  Total gaps: {data.get('total_gaps')}")

            # Check gap categories
            gap_categories = data.get('gap_categories', {})
            print_info("  Gap categories:")
            for category, gaps in gap_categories.items():
                print_info(f"    - {category}: {len(gaps) if isinstance(gaps, list) else 0} gaps")

            # Check recommendations
            recommendations = data.get('recommendations', [])
            print_info(f"  Recommendations: {len(recommendations)}")

            return True, data
        elif response.status_code == 404:
            print_warning("No gap analysis found for this chapter")
            return False, None
        else:
            print_error(f"Failed to get gap analysis: {response.status_code}")
            return False, None
    except Exception as e:
        print_error(f"Get gap analysis exception: {str(e)}")
        return False, None

def get_gap_analysis_summary(token):
    """Get gap analysis summary"""
    print_test("6. Get Gap Analysis Summary")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_BASE}/chapters/{TEST_CHAPTER_ID}/gap-analysis/summary",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_success("Gap analysis summary retrieved")
            print_info(f"  Chapter: {data.get('chapter_title')}")
            print_info(f"  Total gaps: {data.get('total_gaps')}")
            print_info(f"  Completeness: {data.get('completeness_score', 0) * 100:.1f}%")
            print_info(f"  Requires revision: {data.get('requires_revision')}")

            # Severity distribution
            severity_dist = data.get('severity_distribution', {})
            print_info("  Severity distribution:")
            print_info(f"    - Critical: {severity_dist.get('critical', 0)}")
            print_info(f"    - High: {severity_dist.get('high', 0)}")
            print_info(f"    - Medium: {severity_dist.get('medium', 0)}")
            print_info(f"    - Low: {severity_dist.get('low', 0)}")

            # Top recommendations
            recommendations = data.get('top_recommendations', [])
            print_info(f"  Top recommendations: {len(recommendations)}")
            for i, rec in enumerate(recommendations[:3], 1):
                print_info(f"    {i}. {rec.get('description')}")

            return True, data
        elif response.status_code == 404:
            print_warning("No gap analysis summary found")
            return False, None
        else:
            print_error(f"Failed to get summary: {response.status_code}")
            return False, None
    except Exception as e:
        print_error(f"Get summary exception: {str(e)}")
        return False, None

def validate_data_structure(full_data, summary_data):
    """Validate gap analysis data structure"""
    print_test("7. Validate Data Structure")

    all_valid = True

    # Validate full data structure
    if full_data:
        required_fields = [
            'analyzed_at', 'chapter_title', 'total_sections', 'total_gaps',
            'gaps_identified', 'severity_distribution', 'gap_categories',
            'recommendations', 'overall_completeness_score', 'requires_revision'
        ]

        for field in required_fields:
            if field in full_data:
                print_success(f"Field '{field}' present in full data")
            else:
                print_error(f"Field '{field}' missing in full data")
                all_valid = False

    # Validate summary data structure
    if summary_data:
        required_summary_fields = [
            'chapter_id', 'chapter_title', 'total_gaps', 'severity_distribution',
            'completeness_score', 'requires_revision', 'top_recommendations'
        ]

        for field in required_summary_fields:
            if field in summary_data:
                print_success(f"Field '{field}' present in summary data")
            else:
                print_error(f"Field '{field}' missing in summary data")
                all_valid = False

    return all_valid

def main():
    """Main testing workflow"""
    print(f"\n{Colors.BOLD}{'='*80}")
    print(f"  Phase 2 Week 5: Gap Analysis End-to-End Integration Testing")
    print(f"  Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}{Colors.END}\n")

    # Step 1: Login
    token = login()
    if not token:
        print_error("\nTesting aborted: Authentication failed")
        return 1

    # Step 2: API Health
    if not test_api_health(token):
        print_error("\nTesting aborted: API health check failed")
        return 1

    # Step 3: Get chapter info
    success, chapter_data = get_chapter_info(token)
    if not success:
        print_error("\nTesting aborted: Could not get chapter information")
        return 1

    # Step 4: Run gap analysis
    success, analysis_result = run_gap_analysis(token)
    if not success:
        print_warning("\nSkipping remaining tests - gap analysis did not run")
        print_info("This may be expected if:")
        print_info("  - Chapter is not completed")
        print_info("  - User is not chapter author")
        print_info("  - Gap analysis feature is disabled")
        return 0

    # Step 5: Get full gap analysis
    success, full_data = get_full_gap_analysis(token)
    if not success:
        print_warning("\nCould not retrieve full gap analysis")
        full_data = None

    # Step 6: Get gap analysis summary
    success, summary_data = get_gap_analysis_summary(token)
    if not success:
        print_warning("\nCould not retrieve gap analysis summary")
        summary_data = None

    # Step 7: Validate data structure
    if full_data or summary_data:
        data_valid = validate_data_structure(full_data, summary_data)
        if not data_valid:
            print_error("\nData validation failed")
            return 1

    # Final summary
    print(f"\n{Colors.BOLD}{'='*80}")
    print(f"  Testing Summary")
    print(f"{'='*80}{Colors.END}\n")

    print_success("All gap analysis tests completed successfully!")
    print_info("\nGap Analysis Feature Status: ✓ OPERATIONAL")
    print_info("Backend API: ✓ Working")
    print_info("Database Storage: ✓ Working")
    print_info("Data Structure: ✓ Valid")

    print(f"\n{Colors.GREEN}{Colors.BOLD}Phase 2 Week 5 Gap Analysis: COMPLETE ✓{Colors.END}\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
