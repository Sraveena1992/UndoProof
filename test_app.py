from fastapi.testclient import TestClient
from app import app, reset_demo, snapshot

client = TestClient(app)


def setup_function():
    reset_demo()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_allow_changes_only_one_record():
    before = snapshot()
    response = client.post(
        "/demo/allow",
        json={"customer_id": 42, "new_status": "review"},
    )
    assert response.status_code == 200
    result = response.json()
    after = snapshot()
    changed = [key for key in before if before[key] != after[key]]
    assert result["decision"] == "ALLOW"
    assert result["verified"] is True
    assert changed == ["42"]


def test_block_changes_no_records():
    before = snapshot()
    response = client.post("/demo/block")
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "BLOCK"
    assert result["requested_record_count"] == 100
    assert result["changed_record_count"] == 0
    assert result["verified_no_mutation"] is True
    assert snapshot() == before


def test_recover_restores_snapshot():
    before = snapshot()
    response = client.post("/demo/recover")
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "RECOVER"
    assert result["unexpected_ids"] == ["43"]
    assert result["final_state_matches_snapshot"] is True
    assert snapshot() == before


def test_audit_events_are_recorded():
    client.post("/demo/allow", json={"customer_id": 42, "new_status": "review"})
    response = client.get("/audit")
    assert response.status_code == 200
    assert any(item["scenario"] == "allow" for item in response.json())
