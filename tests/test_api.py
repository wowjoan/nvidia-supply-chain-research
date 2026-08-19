from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_company():
    r = client.get("/company")
    assert r.status_code == 200
    body = r.json()
    assert body["subject_company"]["ticker"] == "NVDA"
    assert "not_covered" in body["scope"]


def test_list_relationships_default():
    r = client.get("/relationships")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["items"]) == min(body["total"], 20)
    # 預設依信賴度分數由高到低排序
    scores = [item["confidence_score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)


def test_filter_by_type():
    r = client.get("/relationships", params={"type": "supplier"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert all(item["relationship_type"] == "supplier" for item in body["items"])


def test_filter_by_invalid_type_returns_422():
    r = client.get("/relationships", params={"type": "not_a_real_type"})
    assert r.status_code == 422
    assert "detail" in r.json()


def test_filter_by_invalid_status_returns_422():
    r = client.get("/relationships", params={"status": "made_up_status"})
    assert r.status_code == 422


def test_filter_by_min_score():
    r = client.get("/relationships", params={"min_score": 90})
    assert r.status_code == 200
    body = r.json()
    assert all(item["confidence_score"] >= 90 for item in body["items"])


def test_filter_by_ticker_case_insensitive():
    r = client.get("/relationships", params={"counterparty_ticker": "nvda-not-real"})
    assert r.status_code == 200
    assert r.json()["total"] == 0

    r2 = client.get("/relationships", params={"counterparty_ticker": "tsm"})
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1


def test_pagination_out_of_range_returns_404():
    r = client.get("/relationships", params={"page": 999, "page_size": 5})
    assert r.status_code == 404


def test_pagination_boundaries_rejected_by_validation():
    r = client.get("/relationships", params={"page_size": 0})
    assert r.status_code == 422
    r2 = client.get("/relationships", params={"min_score": 101})
    assert r2.status_code == 422


def test_get_single_relationship_found():
    listing = client.get("/relationships").json()
    first_id = listing["items"][0]["id"]
    r = client.get(f"/relationships/{first_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == first_id
    assert "score_breakdown" in body
    assert body["evidence"], "每筆關係至少要有一則證據"


def test_get_single_relationship_not_found():
    r = client.get("/relationships/does-not-exist-123")
    assert r.status_code == 404


def test_graph_endpoint_structure():
    r = client.get("/graph")
    assert r.status_code == 200
    body = r.json()
    assert body["nodes"]
    assert body["edges"]
    subject_nodes = [n for n in body["nodes"] if n["role"] == "subject"]
    assert len(subject_nodes) == 1
    assert subject_nodes[0]["ticker"] == "NVDA"
    # 每條邊的 source 都應該指向 subject node
    assert all(e["source"] == subject_nodes[0]["id"] for e in body["edges"])


def test_disputed_relationship_has_lower_score_than_similar_confirmed_one():
    """Samsung（disputed）與 SK Hynix（confirmed，同樣是 HBM 供應商）比較，
    驗證『證據矛盾』確實反映在分數上，而不是被靜默忽略。"""
    r = client.get("/relationships", params={"counterparty_ticker": "005930.KS"})
    samsung = r.json()["items"][0]
    assert samsung["status"] == "disputed_conflicting_reports"

    r2 = client.get("/relationships", params={"counterparty_ticker": "000660.KS"})
    skhynix = r2.json()["items"][0]
    assert skhynix["status"] == "confirmed_ongoing"

    assert samsung["score_breakdown"]["status_multiplier"] < skhynix["score_breakdown"]["status_multiplier"]
