import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_cli_company():
    result = run_cli("company")
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["subject_company"]["ticker"] == "NVDA"


def test_cli_relationships_filter_by_type():
    result = run_cli("relationships", "--type", "peer", "--summary-only")
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["total"] > 0
    assert all(item["relationship_type"] == "peer" for item in body["items"])


def test_cli_relationships_invalid_type_exits_nonzero():
    result = run_cli("relationships", "--type", "totally-invalid")
    # argparse 的 choices 驗證會直接讓 argparse 以 exit code 2 中止
    assert result.returncode == 2


def test_cli_show_known_id():
    result = run_cli("show", "nvda-nbis-investor-01")
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["counterparty"]["ticker"] == "NBIS"
    assert body["confidence_score"] > 0


def test_cli_show_unknown_id_exits_nonzero_and_reports_error():
    result = run_cli("show", "does-not-exist")
    assert result.returncode == 1
    assert "not_found" in result.stderr


def test_cli_graph_outputs_valid_json_with_nodes_and_edges():
    result = run_cli("graph")
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert "nodes" in body and "edges" in body
    assert len(body["nodes"]) > 1
