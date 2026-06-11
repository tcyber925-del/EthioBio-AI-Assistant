"""Standalone entry point: python -m evaluation.production"""

from evaluation.production.runner import run_all_production_checks

if __name__ == "__main__":
    results = run_all_production_checks()
    for cat, info in sorted(results.items()):
        status = "PASS" if info["passed"] == info["total"] else "FAIL"
        print(f"[{status}] {cat}: {info['passed']}/{info['total']} (score={info['score']})")
        for c in info.get("checks", []):
            c_status = "✓" if c["passed"] else "✗"
            print(f"  {c_status} {c['check']}: {c['detail']}")
