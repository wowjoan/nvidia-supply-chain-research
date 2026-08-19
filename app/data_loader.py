"""載入 data/ 目錄下的公司資訊與關係資料集，並附加計算後的信賴度分數。"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.scoring import compute_score

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COMPANY_FILE = DATA_DIR / "company.json"
RELATIONSHIPS_FILE = DATA_DIR / "relationships.json"

VALID_RELATIONSHIP_TYPES = {
    "supplier",
    "customer",
    "partner",
    "investor_or_investee",
    "peer",
}
VALID_STATUSES = {
    "confirmed_ongoing",
    "exited_historical",
    "pending_not_definitive",
    "disputed_conflicting_reports",
}


class DataValidationError(ValueError):
    """資料集不符合 schema 基本要求時拋出。"""


def _validate_relationship(rel: dict[str, Any]) -> None:
    required_fields = ["id", "counterparty", "relationship_type", "status", "summary", "evidence"]
    for field in required_fields:
        if field not in rel:
            raise DataValidationError(f"關係紀錄缺少必要欄位 '{field}': {rel.get('id', '<unknown>')}")

    if rel["relationship_type"] not in VALID_RELATIONSHIP_TYPES:
        raise DataValidationError(
            f"未知的 relationship_type '{rel['relationship_type']}' (id={rel['id']})"
        )
    if rel["status"] not in VALID_STATUSES:
        raise DataValidationError(f"未知的 status '{rel['status']}' (id={rel['id']})")
    if not rel["evidence"]:
        raise DataValidationError(f"關係紀錄至少需要一筆 evidence (id={rel['id']})")
    for e in rel["evidence"]:
        for f in ("source_url", "publisher", "published_date", "source_type"):
            if f not in e:
                raise DataValidationError(f"evidence 缺少必要欄位 '{f}' (relationship id={rel['id']})")


@lru_cache(maxsize=1)
def load_company() -> dict[str, Any]:
    with COMPANY_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_relationships_raw() -> tuple[dict[str, Any], ...]:
    with RELATIONSHIPS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for rel in data:
        _validate_relationship(rel)
    # 以 tuple 回傳並搭配 lru_cache，避免呼叫端不小心修改到快取內容
    return tuple(data)


def get_research_as_of() -> date:
    company = load_company()
    return date.fromisoformat(company["research_as_of"])


def load_relationships_scored() -> list[dict[str, Any]]:
    """回傳附加了 confidence_score 與 score_breakdown 的關係清單（深拷貝，可安全修改）。"""
    research_as_of = get_research_as_of()
    enriched = []
    for rel in load_relationships_raw():
        rel_copy = json.loads(json.dumps(rel))  # 深拷貝，避免污染快取
        breakdown = compute_score(rel_copy, research_as_of)
        rel_copy["confidence_score"] = breakdown.final_score
        rel_copy["score_breakdown"] = breakdown.as_dict()
        enriched.append(rel_copy)
    return enriched


def find_relationship(relationship_id: str) -> dict[str, Any] | None:
    for rel in load_relationships_scored():
        if rel["id"] == relationship_id:
            return rel
    return None
