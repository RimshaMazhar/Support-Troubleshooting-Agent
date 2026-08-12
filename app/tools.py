"""
Tools that give the agent access to the *current state* of the fictional
ParcelPilot system: service health, carrier/tracking data, recent logs, and
incident history. These are the "system_data" side of the project, as
opposed to the "docs" side handled by retrieval in ingest.py / retrieval.py.
"""

import csv
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "system_data")


def _path(filename):
    return os.path.join(DATA_DIR, filename)


def get_service_status(service_name: str = "") -> str:
    """Return current health/status of one service, or ALL services if none
    given. Use this for any question about which services are healthy,
    degraded, up, down, or their overall status right now."""
    with open(_path("service_status.json")) as f:
        data = json.load(f)

    services = data["services"]
    if service_name:
        service_name = service_name.strip().lower()
        matches = [s for s in services if s["name"] == service_name]
        if not matches:
            valid = ", ".join(s["name"] for s in services)
            return f"No service named '{service_name}'. Valid services: {valid}"
        s = matches[0]
        return (
            f"Service '{s['name']}': status={s['status']}, "
            f"latency_ms={s['latency_ms']}, reason=\"{s['reason']}\" "
            f"(captured_at {data['captured_at']})"
        )

    lines = [f"Service status as of {data['captured_at']}:"]
    for s in services:
        lines.append(f"  - {s['name']}: {s['status']} ({s['reason']}, {s['latency_ms']}ms)")
    return "\n".join(lines)


def get_carrier_status(order_id: str = "") -> str:
    """Return carrier tracking status for a specific order, or a summary of
    all orders if no order_id is given."""
    with open(_path("carrier_status.json")) as f:
        data = json.load(f)

    if order_id:
        order_id = order_id.strip().upper()
        matches = [o for o in data["orders"] if o["order_id"] == order_id]
        if not matches:
            return f"No carrier data found for order '{order_id}'."
        o = matches[0]
        events = "; ".join(f"{e['status']} at {e['at']}" for e in o["events"])
        return (
            f"Order {o['order_id']}: carrier_status={o['carrier_status']}. "
            f"Events: {events}"
        )

    counts = {}
    for o in data["orders"]:
        counts[o["carrier_status"]] = counts.get(o["carrier_status"], 0) + 1
    summary = ", ".join(f"{k}: {v}" for k, v in counts.items())
    return (
        f"Carrier feed status: {data['status']} "
        f"(captured_at {data['captured_at']}, last_updated {data['last_updated']}). "
        f"Order breakdown -> {summary}"
    )


def search_logs(service: str = "", level: str = "", code: str = "", limit: int = 10) -> str:
    """Search application logs, optionally filtered by service, level (INFO/WARN/ERROR),
    or error code (e.g. 'ORD-500'). Returns the most recent matches first."""
    with open(_path("application_logs.csv")) as f:
        rows = list(csv.DictReader(f))

    def matches(row):
        if service and row["service"].lower() != service.strip().lower():
            return False
        if level and row["level"].upper() != level.strip().upper():
            return False
        if code and code.strip().upper() not in row["code"].upper():
            return False
        return True

    filtered = [r for r in rows if matches(r)]
    filtered.sort(key=lambda r: r["timestamp"], reverse=True)
    filtered = filtered[:limit]

    if not filtered:
        return "No matching log entries found for the given filters."

    lines = [f"Found {len(filtered)} matching log entries (most recent first):"]
    for r in filtered:
        lines.append(
            f"  - {r['timestamp']} [{r['level']}] {r['service']} {r['code']} "
            f"{r['endpoint']} ({r['duration_ms']}ms) - {r['message']}"
        )
    return "\n".join(lines)


_CODE_PREFIX_TO_AREA = {
    "ORD": "orders",
    "TRK": "tracking",
    "AUTH": "auth",
    "DOC": "documents",
    "NTF": "notifications",
    "RPT": "reporting",
    "API": "api",
}


def search_incidents(keyword: str = "", area: str = "", limit: int = 5) -> str:
    """Search past incident history. 'area' filters by affected service (e.g.
    'orders', 'tracking', 'reporting') and is the most reliable filter -- use
    it whenever the question mentions a service or error code from that
    service. 'keyword' matches plain-English incident summary text (e.g.
    'cannot be found', 'returns an error') -- it does NOT match error codes
    like 'ORD-500' directly, since summaries describe symptoms, not codes."""
    with open(_path("incident_history.csv")) as f:
        rows = list(csv.DictReader(f))

    def matches(row, kw, ar):
        if ar and row["area"].lower() != ar.strip().lower():
            return False
        if kw and kw.strip().lower() not in row["summary"].lower():
            return False
        return True

    filtered = [r for r in rows if matches(r, keyword, area)]

    # Fallback: if a keyword looks like an error code (e.g. "ORD-500") and
    # found nothing, map its prefix to the matching service area and retry --
    # incident summaries describe symptoms in plain English, not raw codes.
    if not filtered and keyword and "-" in keyword:
        prefix = keyword.split("-")[0].strip().upper()
        mapped_area = _CODE_PREFIX_TO_AREA.get(prefix)
        if mapped_area:
            filtered = [r for r in rows if matches(r, "", mapped_area)]

    filtered.sort(key=lambda r: r["opened_at"], reverse=True)
    filtered = filtered[:limit]

    if not filtered:
        return "No matching past incidents found."

    lines = [f"Found {len(filtered)} matching past incidents (most recent first):"]
    for r in filtered:
        lines.append(
            f"  - {r['incident_id']} ({r['opened_at']}, area={r['area']}, "
            f"status={r['status']}): {r['summary']} | scope={r['scope']} | "
            f"resolution={r['resolution']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_service_status())
    print()
    print(get_service_status("orders"))
    print()
    print(get_carrier_status())
    print()
    print(search_logs(service="orders", level="ERROR", limit=5))
    print()
    print(search_incidents(area="orders", limit=5))