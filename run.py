"""Entry point. Runs one or all verification arms over a fixed HumanEval subset.

Examples:
  python run.py --arm all
  python run.py --arm gate --limit 5
  python run.py --arm all --mock
  python run.py --arm all --solver-model glm-4.5-flash --reviewer-model glm-4.5-flash
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from arms import ARMS  # noqa: E402
import model as model_mod  # noqa: E402
import report  # noqa: E402
import tasks as tasks_mod  # noqa: E402

BUDGET_USD = 2.0  # hard cap from SPEC.md; guard trips at 80 percent of it


def mock_executor(task, completion):
    """Deterministic fake test verdict for --mock mode: only code produced by a
    revision path passes. Clearly fake, used to validate plumbing."""
    passed = "MOCK_REVISED" in (completion or "")
    return passed, "" if passed else "mock test failure"


def make_clients(solver_model, reviewer_model, usage, mock):
    """Return (solver_client, reviewer_client). Both share one Usage object so
    every model call the arm makes is attributed to that task and arm."""
    if mock:
        solver = model_mod.MockClient()
        reviewer = model_mod.MockClient()
        solver.usage = usage
        reviewer.usage = usage
        return solver, reviewer
    solver = model_mod.Client(solver_model, usage=usage)
    if reviewer_model == solver_model:
        return solver, solver
    return solver, model_mod.Client(reviewer_model, usage=usage)


def run_arm(solver_model, reviewer_model, arm_name, task_list, mock):
    runner = mock_executor if mock else tasks_mod.run_tests
    rows = []
    for task in task_list:
        usage = model_mod.Usage()
        solver, reviewer = make_clients(solver_model, reviewer_model, usage, mock)
        code = ARMS[arm_name](solver, reviewer, task, runner)
        passed, _ = runner(task, code)
        calls, tin, tout = usage.snapshot()
        rows.append({
            "task_id": task["task_id"], "arm": arm_name, "passed": int(bool(passed)),
            "calls": calls, "input_tokens": tin, "output_tokens": tout,
        })
        print(f"  [{arm_name}] {task['task_id']}: {'pass' if passed else 'FAIL'} "
              f"({calls} calls, {tin}+{tout} tok)")
    return rows


def main():
    ap = argparse.ArgumentParser(description="Verification-design benchmark (see SPEC.md)")
    ap.add_argument("--arm", default="all", choices=["all"] + list(ARMS))
    ap.add_argument("--mock", action="store_true", help="deterministic fake solver, no API calls")
    ap.add_argument("--limit", type=int, default=20, help="number of tasks")
    ap.add_argument("--solver-model", default="glm-4.5-flash")
    ap.add_argument("--reviewer-model", default="glm-4.5-flash")
    ap.add_argument("--tasks", default="humaneval", choices=["humaneval", "mini"])
    ap.add_argument("--offset", type=int, default=0,
                    help="skip this many tasks (numeric id order) before selecting")
    ap.add_argument("--csv", default=None, help="alternate results.csv path")
    args = ap.parse_args()

    arm_names = list(ARMS) if args.arm == "all" else [args.arm]
    task_list = tasks_mod.load_tasks(args.limit, source=args.tasks, offset=args.offset)
    print(f"trust-but-verify: {len(task_list)} tasks (offset {args.offset}), arms={arm_names}, "
          f"mock={args.mock}, solver={args.solver_model}, reviewer={args.reviewer_model}")

    all_rows = []
    for arm_name in arm_names:
        all_rows.extend(run_arm(args.solver_model, args.reviewer_model, arm_name, task_list, args.mock))
        if not args.mock:
            cost, _ = report.estimate_usd(all_rows)
            if cost > BUDGET_USD * 0.8:
                print(f"budget guard: estimated {cost:.4f} USD, stopping early")
                break

    csv_path = report.write_csv(
        all_rows,
        path=args.csv or (os.path.join(report.RESULTS_DIR, "results_mock.csv") if args.mock else None),
    )
    stats = report.aggregate(all_rows)
    print("\n" + report.table_md(stats) + "\n")
    if args.mock:
        print("MOCK numbers, not measurements")
    else:
        total_cost, total_tokens = report.estimate_usd(all_rows)
        print(f"total tokens: {int(total_tokens)}, estimated cost: {total_cost:.4f} USD "
              f"(cap {BUDGET_USD} USD)")
    print(f"wrote {csv_path}")

    if args.arm == "all" and not args.mock and len(all_rows) == len(ARMS) * len(task_list):
        meta = {
            "mock": args.mock, "n_tasks": len(task_list),
            "solver_model": args.solver_model, "reviewer_model": args.reviewer_model,
            "title": f"Primary run: {len(task_list)} tasks at offset {args.offset}",
            "note": (f"Tasks: HumanEval sorted by numeric task id, {len(task_list)} tasks "
                     f"starting at offset {args.offset} (offset 0 is HumanEval/0 up)."),
        }
        md = report.results_md(all_rows, stats, meta)
        root = os.path.dirname(os.path.dirname(os.path.abspath(report.__file__)))
        with open(os.path.join(root, "RESULTS.md"), "w", encoding="utf-8", newline="") as f:
            f.write(md)
        print("wrote RESULTS.md")


if __name__ == "__main__":
    main()
