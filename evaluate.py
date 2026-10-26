"""轻量自动评测入口；使用独立临时库，不干扰正在运行的页面。"""
from tempfile import TemporaryDirectory
from pathlib import Path
from datapilot import data
from datapilot.data import build_database
from datapilot.agent import run_analysis

def main():
    with TemporaryDirectory() as folder:
        data.DB = Path(folder) / "evaluation.duckdb"
        build_database(data.DB)
        report = run_analysis("请巡检最近经营表现并解释 GMV 变化")
        checks = {
            "facts_present": report["facts"]["gmv"] > 0,
            "diagnosis_present": len(report["diagnosis"]) > 0,
            "hypothesis_labeled": len(report["hypotheses"]) > 0,
            "causal_claim_guarded": len(report["conclusions"]) == 0,
            "trace_present": len(report["trace"]) >= 5,
        }
        for name, ok in checks.items(): print(f"{'PASS' if ok else 'FAIL'} {name}")
        if not all(checks.values()): raise SystemExit(1)

if __name__ == "__main__": main()

