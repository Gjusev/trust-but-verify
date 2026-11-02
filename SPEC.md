# SPEC: verify-harness

You are developing this project autonomously. Read this spec fully, make sensible decisions without asking questions, and record every non-obvious choice in DECISIONS.md. Do not modify anything outside this directory.

## What this is

A small, self-contained benchmark that compares verification designs for coding agents and reports pass rate plus cost multiplier for each. It is a mini replication of the findings in "Rethinking Verification in Agent Harnesses" (arXiv 2610.34577, Alibaba + Cornell): https://arxiv.org/abs/2610.34577

Key numbers from that paper, for context only (do not present them as your own results):
- They compare 17 verification designs across 7 frontier models on Terminal-Bench and SWE-bench Verified.
- An independent reviewer adds 5.9 to 9.5 points at only 1.13x to 1.25x cost.
- Rejection gates at delivery add about 6 points but cost 1.5x to 1.8x.
- The authors advise against completion-time self-checking.

Your job is to see whether the direction of those findings holds at tiny scale with a cheap model.

## Designs to compare

Exactly four arms:

1. `none` — the agent writes a solution and it is submitted as-is.
2. `selfcheck` — before submitting, the same agent instance is asked to review its own solution once and may revise.
3. `reviewer` — before submitting, a separate independent call (fresh context, same or different cheap model) reviews the solution and may request one revision.
4. `gate` — the solution is run against the task tests; on failure the agent gets the test output and retries, max 2 retries.

Every arm runs the same base solver prompt and the same task set. Record for each task and arm: pass or fail, model calls, input and output tokens.

## Tasks

Use a fixed subset of HumanEval (20 problems is enough, chosen deterministically, for example the first 20 by task id). Tests run locally in-process or via subprocess with a timeout. No GPU, no docker required.

## Model calls

Use an OpenAI-compatible endpoint with a cheap flash-tier model. Get working credentials however is available on this machine (env vars, or the local hermes proxy, or hermes secrets). Hard budget: 2 USD equivalent. If no credentials can be found, implement everything, run the full pipeline in `--mock` mode with a deterministic fake solver, and mark every real-results table as PENDING in RESULTS.md. A mock run with clearly labeled fake numbers is acceptable; invented real-looking numbers are never acceptable.

## Layout

```
README.md
SPEC.md (this file, keep unchanged)
DECISIONS.md
src/
tests/
results/results.csv
RESULTS.md
run.py (single entry point, flags: --arm all|none|selfcheck|reviewer|gate, --mock, --limit N)
LICENSE (MIT)
```

## RESULTS.md

One table: rows = arms, columns = pass rate, avg model calls per task, avg tokens per task, cost multiplier vs `none`. One short paragraph on whether the direction matches the paper. One paragraph on limitations (tiny task set, single model, no Terminal-Bench).

## Style rules

- README starts with what it is and the sentence "A small-scale replication of the verification-design comparison from arXiv 2610.34577."
- Cite the paper. List differences from the paper honestly.
- No em dashes anywhere. No marketing language. English only.
- Code: Python 3.11+, stdlib plus openai client plus pytest. Nothing else.

## Definition of done

- `python run.py --arm all` (or `--mock`) runs end to end on this machine.
- RESULTS.md contains a measured table or explicit PENDING markers.
- `pytest` passes.
- git repo initialized with meaningful commits.
- README, DECISIONS, LICENSE present.
