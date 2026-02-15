#!/usr/bin/env python3
"""Test capabilities endpoint includes new modules."""

import sys
sys.path.insert(0, '/config/.openclaw/workspace/ha-copilot-repo/addons/copilot_core/rootfs/usr/src/app')

from copilot_core.app import create_app
import json


def test_capabilities():
    """Test capabilities endpoint includes new modules."""
    app = create_app()
    client = app.test_client()
    
    response = client.get("/api/v1/capabilities")
    
    if response.status_code != 200:
        print(f"Failed: {response.status_code}")
        print(response.data)
        return False
    
    data = json.loads(response.data)
    
    print("Capabilities response:")
    print(json.dumps(data, indent=2))
    
    # Check for new modules
    modules = data.get("modules", {})
    
    checks = [
        ("vector_store" in modules, "vector_store module exists"),
        ("dashboard" in modules, "dashboard module exists"),
        ("brain_graph" in modules, "brain_graph module exists"),
    ]
    
    all_passed = True
    for check, description in checks:
        status = "✓" if check else "✗"
        print(f"{status} {description}")
        if not check:
            all_passed = False
    
    # Check vector_store has correct endpoints
    if "vector_store" in modules:
        vs = modules["vector_store"]
        endpoints = vs.get("endpoints", [])
        print(f"vector_store endpoints: {endpoints}")
        
        expected_endpoints = [
            "/api/v1/vector/store",
            "/api/v1/vector/search",
            "/api/v1/vector/get/:id",
            "/api/v1/vector/delete/:id",
            "/api/v1/vector/stats",
        ]
        
        for ep in expected_endpoints:
            if ep in endpoints:
                print(f"  ✓ {ep}")
            else:
                print(f"  ✗ {ep} missing")
                all_passed = False
    
    # Check dashboard has correct endpoints
    if "dashboard" in modules:
        db = modules["dashboard"]
        endpoints = db.get("endpoints", [])
        print(f"dashboard endpoints: {endpoints}")
        
        expected_endpoints = [
            "/api/v1/dashboard/brain-summary",
        ]
        
        for ep in expected_endpoints:
            if ep in endpoints:
                print(f"  ✓ {ep}")
            else:
                print(f"  ✗ {ep} missing")
                all_passed = False
    
    return all_passed


if __name__ == "__main__":
    success = test_capabilities()
    sys.exit(0 if success else 1)
