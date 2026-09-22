def test_core_routes_present(route_map):
    expected = {"/health", "/docs", "/scalar", "/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/logout", "/api/v1/me", "/api/v1/users", "/api/v1/notifications", "/api/v1/search", "/api/v1/audit-log", "/api/v1/webhooks", "/api/v1/metrics", "/api/v1/tests/run", "/api/v1/tests/ui"}
    missing = sorted(expected - set(route_map))
    assert not missing, f"Missing routes: {missing}"

def test_every_api_route_has_http_method(route_map):
    bad = [path for path, methods in route_map.items() if path.startswith("/api/") and not methods]
    assert not bad
