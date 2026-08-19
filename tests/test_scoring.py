from datetime import date

from app.scoring import compute_score


def _base_relationship(**overrides):
    rel = {
        "status": "confirmed_ongoing",
        "quantified_terms": {"amount_usd": 1000000},
        "evidence": [
            {
                "publisher": "SEC",
                "published_date": "2026-08-01",
                "source_type": "regulatory_filing",
            }
        ],
    }
    rel.update(overrides)
    return rel


def test_best_case_scores_100():
    rel = _base_relationship(
        evidence=[
            {"publisher": "SEC", "published_date": "2026-08-01", "source_type": "regulatory_filing"},
            {"publisher": "CNBC", "published_date": "2026-08-01", "source_type": "reputable_news"},
            {"publisher": "Company PR", "published_date": "2026-08-01", "source_type": "company_press_release"},
        ]
    )
    breakdown = compute_score(rel, research_as_of=date(2026, 8, 19))
    assert breakdown.final_score == 100
    assert breakdown.evidence_quality == 40
    assert breakdown.source_independence == 20
    assert breakdown.recency == 20
    assert breakdown.quantifiability == 20


def test_single_weak_source_scores_low():
    rel = _base_relationship(
        quantified_terms=None,
        evidence=[
            {
                "publisher": "Some Blog",
                "published_date": "2023-01-01",
                "source_type": "secondary_aggregator",
            }
        ],
    )
    breakdown = compute_score(rel, research_as_of=date(2026, 8, 19))
    # evidence_quality=14, source_independence=6, recency(>730d)=2, quantifiability=0
    assert breakdown.evidence_quality == 14
    assert breakdown.source_independence == 6
    assert breakdown.recency == 2
    assert breakdown.quantifiability == 0
    assert breakdown.final_score == 22


def test_disputed_status_applies_half_multiplier():
    rel = _base_relationship(status="disputed_conflicting_reports")
    confirmed = compute_score({**rel, "status": "confirmed_ongoing"}, research_as_of=date(2026, 8, 19))
    disputed = compute_score(rel, research_as_of=date(2026, 8, 19))
    assert disputed.status_multiplier == 0.5
    assert disputed.final_score == round(confirmed.raw_subtotal * 0.5)
    assert disputed.final_score < confirmed.final_score


def test_pending_status_applies_point_six_multiplier():
    rel = _base_relationship(status="pending_not_definitive")
    breakdown = compute_score(rel, research_as_of=date(2026, 8, 19))
    assert breakdown.status_multiplier == 0.6


def test_missing_evidence_dates_do_not_crash_and_score_zero_recency():
    rel = {
        "status": "confirmed_ongoing",
        "quantified_terms": None,
        "evidence": [{"publisher": "X", "source_type": "reputable_news"}],  # no published_date
    }
    breakdown = compute_score(rel, research_as_of=date(2026, 8, 19))
    assert breakdown.recency == 0


def test_future_dated_evidence_is_clamped_not_negative():
    """證據日期若異常地晚於研究截止日（資料錯誤），不應產生負的年齡或造成例外。"""
    rel = _base_relationship(
        evidence=[
            {
                "publisher": "SEC",
                "published_date": "2099-01-01",
                "source_type": "regulatory_filing",
            }
        ]
    )
    breakdown = compute_score(rel, research_as_of=date(2026, 8, 19))
    assert breakdown.recency == 20
