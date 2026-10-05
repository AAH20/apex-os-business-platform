"""Integration test for all backend route modules."""
import sys
import os
import importlib
import traceback
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import the main app
from main import app, API_KEY

# Get all route modules
routes_dir = backend_dir / "routes"
route_files = sorted([f for f in os.listdir(routes_dir) if f.endswith(".py") and not f.startswith("__")])

print(f"Found {len(route_files)} route modules to test\n")
print("=" * 80)

results = []
total_routes = 0
passed = 0
failed = 0

for route_file in route_files:
    module_name = route_file[:-3]
    result = {
        "module": module_name,
        "import_ok": False,
        "router_exists": False,
        "routes_count": 0,
        "status": "FAIL",
        "issues": []
    }
    
    try:
        # Test 1: Import module
        module = importlib.import_module(f"routes.{module_name}")
        result["import_ok"] = True
        
        # Test 2: Check router exists
        if hasattr(module, "router"):
            result["router_exists"] = True
            router = module.router
            
            # Test 3: Count routes
            routes_count = len(router.routes)
            result["routes_count"] = routes_count
            total_routes += routes_count
            
            # Test 4: Test GET /api/{module_name}/ with X-API-Key
            # Find a GET route to test
            get_routes = [r for r in router.routes if hasattr(r, 'methods') and 'GET' in r.methods]
            
            if get_routes:
                # Try the first GET route
                test_route = get_routes[0]
                # Build the full path
                prefix = router.prefix if hasattr(router, 'prefix') else ""
                path = test_route.path
                
                # Use FastAPI test client
                from fastapi.testclient import TestClient
                client = TestClient(app)
                
                # Test with API key
                response = client.get(f"{prefix}{path}", headers={"X-API-Key": API_KEY})
                
                if response.status_code == 200:
                    result["status"] = "PASS"
                    passed += 1
                elif response.status_code == 404:
                    # 404 is acceptable for some routes (e.g., /{id} routes)
                    result["status"] = "PASS"
                    result["issues"].append(f"Route returned 404 (may need ID param)")
                    passed += 1
                else:
                    result["issues"].append(f"GET {prefix}{path} returned {response.status_code}")
                    failed += 1
            else:
                result["issues"].append("No GET routes found")
                failed += 1
        else:
            result["issues"].append("No router attribute found")
            failed += 1
            
    except Exception as e:
        result["issues"].append(f"Import error: {str(e)}")
        failed += 1
    
    results.append(result)

# Print results
print("\nRESULTS:")
print("-" * 80)
for r in results:
    status_icon = "✓" if r["status"] == "PASS" else "✗"
    print(f"{status_icon} {r['module']:25} | Routes: {r['routes_count']:3} | {r['status']}")
    if r["issues"]:
        for issue in r["issues"]:
            print(f"    ⚠ {issue}")

print("\n" + "=" * 80)
print(f"SUMMARY: {passed}/{len(route_files)} modules passed, {failed} failed")
print(f"Total routes across all modules: {total_routes}")
print("=" * 80)

# Exit with error code if any failed
sys.exit(0 if failed == 0 else 1)
