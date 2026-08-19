"""
ARTi 供應鏈與合作關係研究挑戰 — NVIDIA 研究服務 HTTP API
=======================================================

以 FastAPI 提供三組資源：
- GET /company            研究對象與研究範圍/邊界說明
- GET /relationships      關係列表查詢（可依 type/status/counterparty/min_score 篩選、分頁）
- GET /relationships/{id} 單筆關係詳情（含完整證據與評分明細）
- GET /graph              關係圖資料（nodes + edges），方便前端或 reviewer 視覺化

執行方式見 README「Quickstart」章節。
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app.data_loader import (
    VALID_RELATIONSHIP_TYPES,
    VALID_STATUSES,
    find_relationship,
    load_company,
    load_relationships_scored,
)

app = FastAPI(
    title="ARTi Supply Chain & Partnership Research API",
    description="NVIDIA 供應鏈與合作關係研究服務（求職挑戰交付物）",
    version="1.0.0",
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/company", tags=["meta"])
def company() -> dict:
    return load_company()


@app.get("/relationships", tags=["relationships"])
def list_relationships(
    type: str | None = Query(
        default=None, description=f"關係類型篩選，允許值：{sorted(VALID_RELATIONSHIP_TYPES)}"
    ),
    status: str | None = Query(
        default=None, description=f"關係狀態篩選，允許值：{sorted(VALID_STATUSES)}"
    ),
    counterparty_ticker: str | None = Query(
        default=None, description="依對手方股票代碼篩選（不分大小寫完全比對）"
    ),
    min_score: int | None = Query(
        default=None, ge=0, le=100, description="最低信賴度分數（0-100）"
    ),
    page: int = Query(default=1, ge=1, description="頁碼，從 1 開始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁筆數，1-100"),
):
    if type is not None and type not in VALID_RELATIONSHIP_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"無效的 type='{type}'，允許值：{sorted(VALID_RELATIONSHIP_TYPES)}",
        )
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"無效的 status='{status}'，允許值：{sorted(VALID_STATUSES)}",
        )

    items = load_relationships_scored()

    if type is not None:
        items = [r for r in items if r["relationship_type"] == type]
    if status is not None:
        items = [r for r in items if r["status"] == status]
    if counterparty_ticker is not None:
        needle = counterparty_ticker.strip().upper()
        items = [r for r in items if r["counterparty"]["ticker"].upper() == needle]
    if min_score is not None:
        items = [r for r in items if r["confidence_score"] >= min_score]

    # 依信賴度分數由高到低排序，同分則依 id 排序以確保分頁結果穩定、可重現
    items = sorted(items, key=lambda r: (-r["confidence_score"], r["id"]))

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    if total > 0 and start >= total:
        raise HTTPException(
            status_code=404,
            detail=f"page={page} 超出範圍：共 {total} 筆結果，page_size={page_size}",
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": page_items,
    }


@app.get("/relationships/{relationship_id}", tags=["relationships"])
def get_relationship(relationship_id: str):
    rel = find_relationship(relationship_id)
    if rel is None:
        raise HTTPException(status_code=404, detail=f"找不到 relationship id='{relationship_id}'")
    return rel


@app.get("/graph", tags=["relationships"])
def graph():
    company_info = load_company()["subject_company"]
    items = load_relationships_scored()

    subject_id = company_info["ticker"]
    nodes = {
        subject_id: {
            "id": subject_id,
            "name": company_info["name"],
            "ticker": company_info["ticker"],
            "role": "subject",
        }
    }
    edges = []
    for rel in items:
        cp = rel["counterparty"]
        cp_id = cp["ticker"]
        if cp_id not in nodes:
            nodes[cp_id] = {
                "id": cp_id,
                "name": cp["name"],
                "ticker": cp["ticker"],
                "role": "counterparty",
            }
        edges.append(
            {
                "id": rel["id"],
                "source": subject_id,
                "target": cp_id,
                "relationship_type": rel["relationship_type"],
                "status": rel["status"],
                "confidence_score": rel["confidence_score"],
            }
        )

    return {"nodes": list(nodes.values()), "edges": edges}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):  # pragma: no cover - defensive
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)},
    )
