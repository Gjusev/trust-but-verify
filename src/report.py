"""Aggregation and output: results.csv, summary table, RESULTS.md."""
import csv
import datetime
import os

ARMS = ["none", "selfcheck", "reviewer", "gate"]
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

# Cost estimate basis, USD per 1M tokens. The z.ai docs page for GLM-4.5
# labels GLM-4.5-Flash a free tier and quotes the GLM-4.5 series list price
# at 0.2 input / 1.1 output. We use the flagship list price as a conservative
# upper bound; if Flash is billed at 0 the true cost is lower.
PRICE_PER_MTOK = {"glm-4.5-flash": (0.2, 1.1)}


def aggregate(rows):
    """rows: list of dicts with task_id, arm, passed, calls, input_tokens, output_tokens."""
    out = {}
    for arm in ARMS:
        arm_rows = [r for r in rows if r["arm"] == arm]
        if not arm_rows:
            continue
        n = len(arm_rows)
        out[arm] = {
            "tasks": n,
            "pass_rate": sum(r["passed"] for r in arm_rows) / n,
            "avg_calls": sum(r["calls"] for r in arm_rows) / n,
            "avg_tokens": sum(r["input_tokens"] + r["output_tokens"] for r in arm_rows) / n,
            "avg_input": sum(r["input_tokens"] for r in arm_rows) / n,
            "avg_output": sum(r["output_tokens"] for r in arm_rows) / n,
        }
    base = out.get("none", {}).get("avg_tokens")
    for arm, stats in out.items():
        stats["cost_mult"] = (stats["avg_tokens"] / base) if base else ""
    return out


def fmt(x, digits=2):
    return f"{x:.{digits}f}" if isinstance(x, (int, float)) else str(x)


def table_md(stats):
    lines = [
        "| arm | pass rate | avg calls/task | avg tokens/task | cost mult vs none |",
        "|---|---|---|---|---|",
    ]
    for arm in ARMS:
        if arm not in stats:
            continue
        s = stats[arm]
        mult = fmt(s["cost_mult"]) if s["cost_mult"] != "" else "n/a"
        lines.append(
            f"| {arm} | {fmt(s['pass_rate'] * 100, 1)}% ({int(round(s['pass_rate'] * s['tasks']))}/{s['tasks']}) "
            f"| {fmt(s['avg_calls'])} | {fmt(s['avg_tokens'], 0)} | {mult} |"
        )
    return "\n".join(lines)


def write_csv(rows, path=None):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = path or os.path.join(RESULTS_DIR, "results.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "arm", "passed", "calls", "input_tokens", "output_tokens"])
        for r in rows:
            w.writerow([r["task_id"], r["arm"], int(r["passed"]), r["calls"],
                        r["input_tokens"], r["output_tokens"]])
    return path


def estimate_usd(rows):
    price = PRICE_PER_MTOK.get("glm-4.5-flash", (0, 0))
    tin = sum(r["input_tokens"] for r in rows) / 1e6
    tout = sum(r["output_tokens"] for r in rows) / 1e6
    return tin * price[0] + tout * price[1], tin * 1e6 + tout * 1e6


def results_md(rows, stats, meta):
    """Build the full RESULTS.md content from measured rows."""
    cost, total_tokens = estimate_usd(rows)
    date = datetime.date.today().isoformat()
    if meta.get("mock"):
        banner = (
            "STATUS: MOCK RUN. All numbers below come from the deterministic fake\n"
            "solver and fake test verdicts. They validate plumbing only and are NOT\n"
            "measurements of any model. Real tables: PENDING.\n\n"
        )
        model_line = "model: mock (no API calls)"
    else:
        banner = (
            "STATUS: MEASURED. Numbers below come from the run recorded in\n"
            "results/results.csv on this repository.\n\n"
        )
        model_line = (
            f"solver model: {meta['solver_model']}, reviewer model: {meta['reviewer_model']}, "
            f"temperature 0, thinking disabled"
        )
    table = table_md(stats)
    none = stats.get("none", {})
    rev = stats.get("reviewer", {})
    gate = stats.get("gate", {})
    selfc = stats.get("selfcheck", {})
    rev_delta = (rev.get("pass_rate", 0) - none.get("pass_rate", 0)) * 100
    gate_delta = (gate.get("pass_rate", 0) - none.get("pass_rate", 0)) * 100
    selfc_delta = (selfc.get("pass_rate", 0) - none.get("pass_rate", 0)) * 100
    parts = []
    parts.append("# RESULTS\n")
    parts.append(banner.rstrip())
    parts.append(f"Run date: {date}. Tasks: {meta['n_tasks']} HumanEval problems "
                 f"(first {meta['n_tasks']} by numeric task id). {model_line}.\n")
    parts.append(table + "\n")
    parts.append(f"Total tokens across the run: {int(total_tokens)}. Estimated cost: "
                 f"{cost:.4f} USD (upper bound, glm-4.5 series list price 0.2/1.1 USD per "
                 f"Mtok; the docs label glm-4.5-flash a free tier). Budget cap: 2 USD.\n")
    parts.append("## Does the direction match the paper\n")
    parts.append(
        f"At this scale the reviewer arm changed the pass rate by {rev_delta:+.1f} points "
        f"at {fmt(rev.get('cost_mult', 'n/a'))}x the token cost of the none arm, the gate arm "
        f"by {gate_delta:+.1f} points at {fmt(gate.get('cost_mult', 'n/a'))}x, and the selfcheck "
        f"arm by {selfc_delta:+.1f} points. The paper (arXiv 2610.34577) reports an independent "
        f"reviewer adding 5.9 to 9.5 points at 1.13x to 1.25x cost and rejection gates adding "
        f"about 6 points at 1.5x to 1.8x, and advises against completion-time self-checking. "
        f"Whether these tiny-scale deltas agree in sign with those ranges is readable directly "
        f"from the table above; with {meta['n_tasks']} tasks each task is 5 points, so any "
        f"comparison is directional at best.\n"
    )
    parts.append("## Limitations\n")
    parts.append(
        "- 20 HumanEval problems only: one flipped task moves the pass rate by 5 points.\n"
        "- One model (a flash tier), one temperature (0), one run per arm: no error bars.\n"
        "- HumanEval is function synthesis from docstrings, far easier and more self-contained "
        "than Terminal-Bench or SWE-bench Verified, where the paper located its findings.\n"
        "- The gate arm sees the bundled tests, which rewards fitting those exact asserts.\n"
        "- Token counts proxy cost; the price conversion is an estimate, not an invoice.\n"
    )
    parts.append(
        "Compared designs are from Rethinking Verification in Agent Harnesses, "
        "arXiv 2610.34577 (https://arxiv.org/abs/2610.34577). This repository is a "
        "small independent check of the direction of those findings, not a reproduction.\n"
    )
    return "\n".join(parts)
