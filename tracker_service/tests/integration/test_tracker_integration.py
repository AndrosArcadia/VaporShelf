from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_multiuser_reading_progress():
    p1 = {"user_id": "usr-102", "current_page": 42, "total_pages": 300}
    p2 = {"user_id": "usr-999", "current_page": 150, "total_pages": 300}

    assert client.put("/documents/doc-1/progress", json=p1).status_code == 200
    assert client.put("/documents/doc-1/progress", json=p2).status_code == 200

    res1 = client.get("/documents/doc-1/progress", params={"user_id": "usr-102"})
    res2 = client.get("/documents/doc-1/progress", params={"user_id": "usr-999"})

    assert res1.status_code == 200
    assert res1.json()["current_page"] == 42
    assert res2.status_code == 200
    assert res2.json()["current_page"] == 150
