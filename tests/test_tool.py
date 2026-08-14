from app.tools import get_service_status, get_carrier_status, search_logs, search_incidents


def test_get_service_status_all():
    result = get_service_status()
    assert "api" in result
    assert "orders" in result


def test_get_service_status_single_known_service():
    result = get_service_status("orders")
    assert "orders" in result.lower()
    assert "status=" in result


def test_get_service_status_unknown_service():
    result = get_service_status("not_a_real_service")
    assert "No service named" in result


def test_get_carrier_status_summary():
    result = get_carrier_status()
    assert "Carrier feed status" in result


def test_get_carrier_status_unknown_order():
    result = get_carrier_status("ORD-9999999")
    assert "No carrier data found" in result


def test_search_logs_filters_by_service_and_level():
    result = search_logs(service="orders", level="ERROR", limit=5)
    assert "orders" in result.lower()
    assert "ERROR" in result


def test_search_logs_partial_code_match():
    result = search_logs(code="500", limit=5)
    assert "ORD-500" in result or "API-500" in result


def test_search_incidents_by_area():
    result = search_incidents(area="orders", limit=5)
    assert "orders" in result.lower()


def test_search_incidents_error_code_fallback():
    result = search_incidents(keyword="ORD-500", limit=5)
    assert "No matching past incidents" not in result