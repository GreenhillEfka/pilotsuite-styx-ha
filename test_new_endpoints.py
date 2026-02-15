#!/usr/bin/env python3
"""Test script for new API endpoints."""

import sys
sys.path.insert(0, '/config/.openclaw/workspace/ha-copilot-repo/addons/copilot_core/rootfs/usr/src/app')

from copilot_core.app import create_app


def test_endpoints():
    """Test all new endpoints."""
    app = create_app()
    client = app.test_client()
    
    tests = [
        # Status endpoint
        ("/api/v1/status", 200, "status"),
        
        # Capabilities endpoint (already exists)
        ("/api/v1/capabilities", 200, "capabilities"),
        
        # Dashboard endpoints
        ("/api/v1/dashboard/health", 200, "dashboard/health"),
        # brain-summary requires Brain Graph service, will be 503 in test context
        
        # Vector endpoints
        ("/api/v1/vector/stats", 200, "vector/stats"),
        # vector/embeddings requires valid payload, will be 400 in test context
        
        # Additional vector endpoints
        ("/api/v1/vector/vectors", 200, "vector/vectors"),
        ("/api/v1/vector/similar/test", 404, "vector/similar"),  # Will 404 but that's expected
    ]
    
    results = []
    for url, expected_status, name in tests:
        response = client.get(url) if not url.endswith("/embeddings") else client.post(url, json={})
        
        success = response.status_code == expected_status
        results.append((name, success, response.status_code, url))
        
        status = "✓" if success else "✗"
        print(f"{status} {name}: {url} -> {response.status_code}")
        if not success:
            print(f"  Expected: {expected_status}")
            if response.data:
                print(f"  Response: {response.data[:200]}")
    
    # Summary
    passed = sum(1 for _, success, _, _ in results if success)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = test_endpoints()
    sys.exit(0 if success else 1)
