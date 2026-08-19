"""API 回應用的 Pydantic 模型（僅用於序列化/文件展示，資料本身以 dict 形式在 app 內流動）。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RelationshipType = Literal["supplier", "customer", "partner", "investor_or_investee", "peer"]
RelationshipStatus = Literal[
    "confirmed_ongoing", "exited_historical", "pending_not_definitive", "disputed_conflicting_reports"
]


class Counterparty(BaseModel):
    name: str
    ticker: str
    exchange: str


class Evidence(BaseModel):
    source_url: str
    publisher: str
    published_date: str
    source_type: str
    accessed_date: str | None = None
    evidence_locator: str | None = None


class ScoreBreakdown(BaseModel):
    evidence_quality: int
    source_independence: int
    recency: int
    quantifiability: int
    status_multiplier: float
    raw_subtotal: int
    final_score: int


class Relationship(BaseModel):
    id: str
    counterparty: Counterparty
    relationship_type: RelationshipType
    direction: str
    status: RelationshipStatus
    summary: str
    quantified_terms: dict[str, Any] | None = None
    evidence: list[Evidence]
    notes: str | None = None
    confidence_score: int
    score_breakdown: ScoreBreakdown


class RelationshipList(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Relationship]


class ErrorResponse(BaseModel):
    error: str
    detail: str


class GraphNode(BaseModel):
    id: str
    name: str
    ticker: str
    role: Literal["subject", "counterparty"]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: RelationshipType
    status: RelationshipStatus
    confidence_score: int


class Graph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
