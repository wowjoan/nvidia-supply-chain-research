#!/usr/bin/env python3
"""
可脚本化 CLI 入口，不需啟動 HTTP 伺服器即可查詢同一份資料集。

範例：
    python cli.py relationships --type supplier
    python cli.py relationships --status disputed_conflicting_reports
    python cli.py relationships --min-score 70 --sort score
    python cli.py show nvda-nbis-investor-01
    python cli.py graph
    python cli.py company

所有輸出皆為 JSON，方便與其他腳本串接（例如 `| jq`）。
"""

from __future__ import annotations

import argparse
import json
import sys

from app.data_loader import (
    VALID_RELATIONSHIP_TYPES,
    VALID_STATUSES,
    find_relationship,
    load_company,
    load_relationships_scored,
)


def cmd_company(_args: argparse.Namespace) -> int:
    print(json.dumps(load_company(), ensure_ascii=False, indent=2))
    return 0


def cmd_relationships(args: argparse.Namespace) -> int:
    if args.type is not None and args.type not in VALID_RELATIONSHIP_TYPES:
        print(
            json.dumps(
                {
                    "error": "invalid_type",
                    "detail": f"允許值：{sorted(VALID_RELATIONSHIP_TYPES)}",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    if args.status is not None and args.status not in VALID_STATUSES:
        print(
            json.dumps(
                {"error": "invalid_status", "detail": f"允許值：{sorted(VALID_STATUSES)}"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    items = load_relationships_scored()
    if args.type is not None:
        items = [r for r in items if r["relationship_type"] == args.type]
    if args.status is not None:
        items = [r for r in items if r["status"] == args.status]
    if args.ticker is not None:
        needle = args.ticker.strip().upper()
        items = [r for r in items if r["counterparty"]["ticker"].upper() == needle]
    if args.min_score is not None:
        items = [r for r in items if r["confidence_score"] >= args.min_score]

    if args.sort == "score":
        items = sorted(items, key=lambda r: (-r["confidence_score"], r["id"]))
    else:
        items = sorted(items, key=lambda r: r["id"])

    if args.summary_only:
        items = [
            {
                "id": r["id"],
                "counterparty": r["counterparty"]["name"],
                "ticker": r["counterparty"]["ticker"],
                "relationship_type": r["relationship_type"],
                "status": r["status"],
                "confidence_score": r["confidence_score"],
            }
            for r in items
        ]

    print(json.dumps({"total": len(items), "items": items}, ensure_ascii=False, indent=2))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    rel = find_relationship(args.id)
    if rel is None:
        print(
            json.dumps({"error": "not_found", "detail": f"id='{args.id}' 不存在"}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(rel, ensure_ascii=False, indent=2))
    return 0


def cmd_graph(_args: argparse.Namespace) -> int:
    from app.main import graph as graph_fn

    print(json.dumps(graph_fn(), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py", description="ARTi NVIDIA 供應鏈與合作關係研究 CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("company", help="顯示研究對象與範圍說明").set_defaults(func=cmd_company)

    p_rel = sub.add_parser("relationships", help="列出關係（可篩選）")
    p_rel.add_argument("--type", choices=sorted(VALID_RELATIONSHIP_TYPES), default=None)
    p_rel.add_argument("--status", choices=sorted(VALID_STATUSES), default=None)
    p_rel.add_argument("--ticker", default=None, help="依對手方股票代碼篩選")
    p_rel.add_argument("--min-score", type=int, default=None, dest="min_score")
    p_rel.add_argument("--sort", choices=["score", "id"], default="score")
    p_rel.add_argument("--summary-only", action="store_true", help="只輸出精簡欄位")
    p_rel.set_defaults(func=cmd_relationships)

    p_show = sub.add_parser("show", help="顯示單筆關係完整內容")
    p_show.add_argument("id")
    p_show.set_defaults(func=cmd_show)

    sub.add_parser("graph", help="輸出關係圖 nodes/edges JSON").set_defaults(func=cmd_graph)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
