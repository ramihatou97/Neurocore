#!/usr/bin/env python3
"""
Test script to verify the 7 new Redis methods work correctly
Tests: zrevrange, zcount, zcard, zrem, zrangebyscore, zremrangebyscore, hlen
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.config.redis import redis_manager


def test_redis_methods():
    """Test all 7 new Redis methods"""

    print("=" * 60)
    print("Testing 7 New Redis Methods")
    print("=" * 60)

    # Initialize Redis
    try:
        redis_manager.initialize()
        print("✓ Redis connection initialized")
    except Exception as e:
        print(f"✗ Failed to initialize Redis: {e}")
        return False

    # Test key names
    test_sorted_set = "test:sorted_set"
    test_hash = "test:hash"

    # Cleanup before tests
    redis_manager.delete(test_sorted_set, test_hash)

    passed = 0
    failed = 0

    # ==================== Test 1: zadd (existing method, setup) ====================
    print("\n[Setup] Testing zadd (existing method)...")
    try:
        members = {
            "member1": 1.0,
            "member2": 2.0,
            "member3": 3.0,
            "member4": 4.0,
            "member5": 5.0
        }
        result = redis_manager.zadd(test_sorted_set, members, serialize="string")
        assert result == 5, f"Expected 5 members added, got {result}"
        print(f"  ✓ Added 5 members to sorted set")
    except Exception as e:
        print(f"  ✗ Setup failed: {e}")
        return False

    # ==================== Test 2: zrevrange ====================
    print("\n[Test 1/7] Testing zrevrange (reverse order)...")
    try:
        result = redis_manager.zrevrange(test_sorted_set, 0, 2, deserialize="string")
        expected = ["member5", "member4", "member3"]  # Highest to lowest
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"  ✓ zrevrange returned: {result}")
        passed += 1
    except Exception as e:
        print(f"  ✗ zrevrange failed: {e}")
        failed += 1

    # ==================== Test 3: zcount ====================
    print("\n[Test 2/7] Testing zcount (count in range)...")
    try:
        result = redis_manager.zcount(test_sorted_set, 2.0, 4.0)
        expected = 3  # member2, member3, member4
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"  ✓ zcount returned: {result} members in range [2.0, 4.0]")
        passed += 1
    except Exception as e:
        print(f"  ✗ zcount failed: {e}")
        failed += 1

    # ==================== Test 4: zcard ====================
    print("\n[Test 3/7] Testing zcard (get total size)...")
    try:
        result = redis_manager.zcard(test_sorted_set)
        expected = 5
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"  ✓ zcard returned: {result} total members")
        passed += 1
    except Exception as e:
        print(f"  ✗ zcard failed: {e}")
        failed += 1

    # ==================== Test 5: zrangebyscore ====================
    print("\n[Test 4/7] Testing zrangebyscore (get by score range)...")
    try:
        result = redis_manager.zrangebyscore(test_sorted_set, 2.0, 4.0, deserialize="string")
        expected = ["member2", "member3", "member4"]
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"  ✓ zrangebyscore returned: {result}")
        passed += 1
    except Exception as e:
        print(f"  ✗ zrangebyscore failed: {e}")
        failed += 1

    # ==================== Test 6: zrem ====================
    print("\n[Test 5/7] Testing zrem (remove members)...")
    try:
        result = redis_manager.zrem(test_sorted_set, "member3", serialize="string")
        assert result == 1, f"Expected 1 member removed, got {result}"

        # Verify removal
        size = redis_manager.zcard(test_sorted_set)
        assert size == 4, f"Expected 4 members remaining, got {size}"
        print(f"  ✓ zrem removed 1 member, {size} remaining")
        passed += 1
    except Exception as e:
        print(f"  ✗ zrem failed: {e}")
        failed += 1

    # ==================== Test 7: zremrangebyscore ====================
    print("\n[Test 6/7] Testing zremrangebyscore (remove by score range)...")
    try:
        result = redis_manager.zremrangebyscore(test_sorted_set, 1.0, 2.0)
        assert result == 2, f"Expected 2 members removed, got {result}"

        # Verify removal
        size = redis_manager.zcard(test_sorted_set)
        assert size == 2, f"Expected 2 members remaining, got {size}"
        print(f"  ✓ zremrangebyscore removed 2 members, {size} remaining")
        passed += 1
    except Exception as e:
        print(f"  ✗ zremrangebyscore failed: {e}")
        failed += 1

    # ==================== Test 8: hlen ====================
    print("\n[Test 7/7] Testing hlen (hash length)...")
    try:
        # Setup hash
        redis_manager.hset(test_hash, "field1", "value1", serialize="string")
        redis_manager.hset(test_hash, "field2", "value2", serialize="string")
        redis_manager.hset(test_hash, "field3", "value3", serialize="string")

        result = redis_manager.hlen(test_hash)
        expected = 3
        assert result == expected, f"Expected {expected} fields, got {result}"
        print(f"  ✓ hlen returned: {result} fields in hash")
        passed += 1
    except Exception as e:
        print(f"  ✗ hlen failed: {e}")
        failed += 1

    # Cleanup
    redis_manager.delete(test_sorted_set, test_hash)
    print("\n✓ Cleanup completed")

    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed out of 7 tests")
    print("=" * 60)

    if failed == 0:
        print("✓ All Redis methods working correctly!")
        return True
    else:
        print(f"✗ {failed} test(s) failed - please review")
        return False


if __name__ == "__main__":
    success = test_redis_methods()
    sys.exit(0 if success else 1)
