from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_private_document_workflow():
    payload = {
        "title": "Arquitectura Cloud Native",
        "is_private": True,
        "file_type": "pdf",
        "owner_id": "usr-101",
    }
    create_res = client.post("/documents", json=payload)
    assert create_res.status_code == 201
    doc_id = create_res.json()["id"]

    denied_res = client.get(f"/documents/{doc_id}", params={"user_id": "usr-102"})
    assert denied_res.status_code == 403

    req_res = client.post(
        f"/documents/{doc_id}/access-requests",
        json={"requester_id": "usr-102"},
    )
    assert req_res.status_code == 201

    approve_res = client.put(
        f"/documents/{doc_id}/access-requests/usr-102",
        json={"owner_id": "usr-101", "approved": True},
    )
    assert approve_res.status_code == 200

    ok_res = client.get(f"/documents/{doc_id}", params={"user_id": "usr-102"})
    assert ok_res.status_code == 200
    assert doc_id in ok_res.json()["download_url"]
