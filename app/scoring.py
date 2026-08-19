"""
信賴度／相關度評分模組 (Confidence Scoring Engine)
==================================================

設計理念
--------
挑戰題要求「為關聯上市公司提供 0-100 相關度或置信度，並說明證據可信度、獨立性、
時效性、關係類型和可量化資訊如何影響評分」。本模組將評分邏輯寫成可重現、可測試
的程式碼，而非人工拍腦袋給分——同一筆關係如果換了新的證據（例如多了一篇報導、
或事件過期），重新呼叫 compute_score() 就會得到不同但可解釋的分數。

總分 0-100，由四個維度相加後乘上「關係狀態調整係數」：

1. evidence_quality（最高 40 分）——採用該筆關係「證據陣列中等級最高的來源」計分：
   - regulatory_filing（監理揭露文件，如 SEC 10-K / 8-K）        40
   - company_press_release（公司官方新聞稿）                      36
   - reputable_news（具編輯把關的主流財經/產業媒體）              26
   - secondary_aggregator（個人部落格、聚合分析、未具名轉述）      14
   理由：一手、受法律責任約束的揭露文件最可信；純粹的第三方歸類
   （例如「業界普遍認為 A 是 B 的競爭對手」）最不可信。

2. source_independence（最高 20 分）——依證據陣列中「不重複 publisher 數量」計分：
   - ≥3 家不同出處                 20
   - 2 家不同出處                   14
   - 1 家出處                        6
   理由：多家獨立來源交叉確認，比單一來源更不容易是誤報或公關話術。

3. recency（最高 20 分）——依「研究截止日」與「證據陣列中最新一則 published_date」
   的天數差計分（隨時間衰減）：
   - ≤90 天    20
   - ≤180 天   16
   - ≤365 天   10
   - ≤730 天    5
   - >730 天    2
   理由：供應鏈與合作關係變動快，越舊的揭露對「目前是否仍然成立」的參考價值越低。

4. quantifiability（最高 20 分）——依 quantified_terms 是否含有可驗證的數字欄位：
   - 含至少一個數字型欄位（金額、股數、百分比、GW 容量等）  20
   - 僅有定性說明（例如 note 字串，無數字）                 5
   - 完全沒有 quantified_terms                            0
   理由：「NVIDIA 投資 Intel 50 億美元」比「NVIDIA 與 Intel 有合作」更可驗證、
   也更有評估價值。

關係狀態調整係數（status multiplier）
--------------------------------------
上述四維度加總後（原始滿分 100），會再乘上一個反映「這筆關係目前是否穩固」的
係數：

- confirmed_ongoing         x1.00  （證據支持關係目前持續存在）
- exited_historical         x1.00  （證據清楚支持「關係已結束」這個事實本身，
                                     信賴度不打折，但使用端應理解這是歷史關係）
- pending_not_definitive    x0.60  （雙方僅簽署意向書/未完成具法律約束力協議，
                                     實際是否會如期履行仍有不確定性）
- disputed_conflicting_reports x0.50  （不同時間點/不同來源的報導方向互相矛盾，
                                     刻意大幅降分以避免誤導使用者信以為真）

最終分數 = round(min(100, (evidence_quality + source_independence + recency
                          + quantifiability) * status_multiplier))
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


SOURCE_TYPE_SCORES: dict[str, int] = {
    "regulatory_filing": 40,
    "company_press_release": 36,
    "reputable_news": 26,
    "secondary_aggregator": 14,
}

STATUS_MULTIPLIERS: dict[str, float] = {
    "confirmed_ongoing": 1.0,
    "exited_historical": 1.0,
    "pending_not_definitive": 0.6,
    "disputed_conflicting_reports": 0.5,
}

RECENCY_BUCKETS: list[tuple[int, int]] = [
    (90, 20),
    (180, 16),
    (365, 10),
    (730, 5),
]
RECENCY_FALLBACK = 2


@dataclass(frozen=True)
class ScoreBreakdown:
    evidence_quality: int
    source_independence: int
    recency: int
    quantifiability: int
    status_multiplier: float
    raw_subtotal: int
    final_score: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_quality": self.evidence_quality,
            "source_independence": self.source_independence,
            "recency": self.recency,
            "quantifiability": self.quantifiability,
            "status_multiplier": self.status_multiplier,
            "raw_subtotal": self.raw_subtotal,
            "final_score": self.final_score,
        }


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _evidence_quality(evidence: list[dict[str, Any]]) -> int:
    if not evidence:
        return 0
    return max(SOURCE_TYPE_SCORES.get(e.get("source_type", ""), 0) for e in evidence)


def _source_independence(evidence: list[dict[str, Any]]) -> int:
    publishers = {e.get("publisher") for e in evidence if e.get("publisher")}
    n = len(publishers)
    if n >= 3:
        return 20
    if n == 2:
        return 14
    if n == 1:
        return 6
    return 0


def _recency(evidence: list[dict[str, Any]], research_as_of: date) -> int:
    dates = [_parse_date(e["published_date"]) for e in evidence if e.get("published_date")]
    if not dates:
        return 0
    most_recent = max(dates)
    age_days = (research_as_of - most_recent).days
    if age_days < 0:
        # 證據日期晚於研究截止日，視為資料異常，仍給予最高分但不外推
        age_days = 0
    for threshold, points in RECENCY_BUCKETS:
        if age_days <= threshold:
            return points
    return RECENCY_FALLBACK


def _quantifiability(quantified_terms: dict[str, Any] | None) -> int:
    if not quantified_terms:
        return 0
    numeric_keys = [
        k for k, v in quantified_terms.items() if isinstance(v, (int, float)) and k != "note"
    ]
    if numeric_keys:
        return 20
    return 5


def compute_score(relationship: dict[str, Any], research_as_of: date) -> ScoreBreakdown:
    """依單筆關係紀錄計算 0-100 信賴度分數，回傳可解釋的分項明細。"""
    evidence = relationship.get("evidence", [])
    status = relationship.get("status", "confirmed_ongoing")

    eq = _evidence_quality(evidence)
    si = _source_independence(evidence)
    rc = _recency(evidence, research_as_of)
    qf = _quantifiability(relationship.get("quantified_terms"))

    subtotal = eq + si + rc + qf
    multiplier = STATUS_MULTIPLIERS.get(status, 1.0)
    final = round(min(100, subtotal * multiplier))
    final = max(0, final)

    return ScoreBreakdown(
        evidence_quality=eq,
        source_independence=si,
        recency=rc,
        quantifiability=qf,
        status_multiplier=multiplier,
        raw_subtotal=subtotal,
        final_score=final,
    )
