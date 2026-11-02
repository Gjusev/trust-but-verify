# verify-harness

A small benchmark that compares four verification designs for coding agents on a
fixed HumanEval subset and reports pass rate and token cost for each.
A small-scale replication of the verification-design comparison from arXiv 2610.34577.

The compared designs come from "Rethinking Verification in Agent Harnesses"
(arXiv 2610.34577, https://arxiv.org/abs/2610.34577). This repository does not
reproduce that paper. It checks whether the direction of three of its findings
holds at tiny scale with one cheap model:

- an independent reviewer improves results at modest extra cost,
- test-based rejection gates improve results at higher extra cost,
- completion-time self-checking is not worth its cost.

The four arms, sharing one base solver prompt and one task set:

| arm | what happens before submission |
|---|---|
| `none` | nothing, the solution is submitted as-is |
| `selfcheck` | the same agent instance reviews its own solution once and may revise |
| `reviewer` | a separate fresh-context call reviews and may request one revision |
| `gate` | the solution runs against the task tests; on failure the agent sees the test output and retries, max 2 retries |

Per task and arm the harness records pass or fail, model call count, and input
and output tokens.

## Usage

Requires Python 3.11+ and the `openai` and `pytest` packages.

```
python run.py --arm all            # full run, all four arms, 20 tasks
python run.py --arm gate           # one arm
python run.py --arm all --limit 5  # fewer tasks
python run.py --arm all --mock     # deterministic fake solver, no API calls
python run.py --arm all --solver-model MODEL --reviewer-model MODEL
```

The API key is read from `ZAI_API_KEY` and the endpoint from `ZAI_BASE_URL`
(default `https://api.z.ai/api/paas/v4`). Measured output lands in
`results/results.csv` and `RESULTS.md`. Tests: `pytest`.

## Differences from the paper

The paper compares 17 verification designs across 7 frontier models on
Terminal-Bench and SWE-bench Verified. This repository differs in every
dimension except the shape of the question:

- 4 designs instead of 17; the arms are simplified analogues, not ports.
- 1 flash-tier model (glm-4.5-flash) instead of 7 frontier models.
- 20 HumanEval problems instead of two agentic software-engineering benchmarks.
- Pass/fail against bundled unit tests instead of agentic task completion.
- Token counts as the cost proxy instead of dollars per run.
- One run per arm, temperature 0, no repeats and no error bars.

Numbers in RESULTS.md are therefore directional only. See DECISIONS.md for
every non-obvious implementation choice.

## Layout

```
run.py              entry point
src/model.py        API client, usage tracking, mock client
src/tasks.py        HumanEval loading, fallback set, sandboxed test runner
src/arms.py         the four verification arms
src/report.py       aggregation, results.csv, RESULTS.md
tests/              pytest suite (no network needed)
data/HumanEval.jsonl  cached task set (MIT licensed, openai/human-eval)
results/results.csv   per-task, per-arm measurements
```

## License

MIT, see LICENSE. The bundled HumanEval data follows its own MIT license
(https://github.com/openai/human-eval).
