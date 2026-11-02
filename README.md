# verify-harness

All three verification designs bought the same +5 pass-rate points on the hard
subset, at 1.50x (gate), 2.73x (selfcheck) and 3.56x (reviewer) the token cost
of no verification.

## What this is

verify-harness runs one Python coding agent under four verification designs on
fixed HumanEval subsets and reports pass rate and token cost per design. It is
a mini replication of the comparison in Rethinking Verification in Agent
Harnesses (arXiv 2610.34577, Alibaba and Cornell), run at a scale where the
direction of that paper's findings can be checked but their size cannot; it
makes no novelty claim.

## Arms

| arm | what happens before submission |
|---|---|
| `none` | nothing, the solution is submitted as-is |
| `selfcheck` | the same agent instance reviews its own solution once and may revise |
| `reviewer` | a separate fresh-context call reviews and may request one revision |
| `gate` | the solution runs against the task tests; on failure the agent sees the test output and retries, max 2 retries |

## Results

Measured 2026-11-02. Solver and reviewer are both glm-4.5-flash, temperature 0,
thinking disabled, one run per arm. Per-task rows and raw console logs are in
the repo (`results/*.csv`, `run_output*.txt`); RESULTS.md is the source for
every number below.

### Hard subset: last 20 HumanEval tasks (HumanEval/144 to /163)

The only measured subset with headroom below the ceiling. It was chosen after
the first-20 subset saturated; the selection procedure is in DECISIONS.md.

| arm | pass rate | avg calls/task | avg tokens/task | cost mult vs none |
|---|---|---|---|---|
| none | 85.0% (17/20) | 1.00 | 325 | 1.00 |
| selfcheck | 90.0% (18/20) | 2.00 | 887 | 2.73 |
| reviewer | 90.0% (18/20) | 2.15 | 1155 | 3.56 |
| gate | 90.0% (18/20) | 1.25 | 487 | 1.50 |

### First 20 HumanEval tasks (HumanEval/0 to /19): saturated

glm-4.5-flash solves all 20 tasks first try, so every arm scores 20/20 and
verification deltas are structurally zero. The cost multipliers still differ
and are reported as measured.

| arm | pass rate | avg calls/task | avg tokens/task | cost mult vs none |
|---|---|---|---|---|
| none | 100.0% (20/20) | 1.00 | 285 | 1.00 |
| selfcheck | 100.0% (20/20) | 2.00 | 769 | 2.70 |
| reviewer | 100.0% (20/20) | 2.00 | 660 | 2.32 |
| gate | 100.0% (20/20) | 1.00 | 284 | 1.00 |

### Headline finding, sign only

Every delta on the hard subset is exactly one task out of 20, so 5 points. On
a subset this size the data supports a direction, not a size:

- gate matches the paper on direction and cost range: +5 points at 1.50x here
  against the paper's about 6 points at 1.5x to 1.8x.
- reviewer matches the paper's direction (+5 points) but not its cost: 3.56x
  here against the paper's 1.13x to 1.25x. The base arm here is a single short
  call, so every verification turn pays full context again.
- selfcheck gained +5 points at 2.73x, which diverges from the paper's advice
  against completion-time self-checking.

## Quickstart

Python 3.11+ with the `openai` and `pytest` packages. The API key is read from
the `ZAI_API_KEY` environment variable; the endpoint defaults to
`https://api.z.ai/api/paas/v4` and can be overridden with `ZAI_BASE_URL`.

```sh
export ZAI_API_KEY=...
python run.py --arm all                          # all four arms, first 20 tasks
python run.py --arm all --offset 144             # the hard subset above
python run.py --arm all --limit 5                # fewer tasks
python run.py --arm gate                         # one arm
python run.py --arm all --mock                   # deterministic fake solver, no API calls
python run.py --arm all --solver-model MODEL --reviewer-model MODEL
```

Flags: `--arm {none,selfcheck,reviewer,gate,all}`, `--limit N`, `--offset N`
(numeric task-id order), `--mock`, `--solver-model`, `--reviewer-model`, plus
`--tasks mini` (bundled 4-task fallback set, no network) and `--csv PATH`.
Measured rows land in `results/results.csv` or the `--csv` path; a full
non-mock `--arm all` run also rewrites RESULTS.md. Tests: `pytest`.

## Method

- Task set: HumanEval, sorted by numeric task id, fixed 20-task slices selected
  by `--offset`. The dataset is cached in `data/HumanEval.jsonl` so reruns need
  no network.
- Scoring: prompt + completion + the task's own test block is written to a temp
  file and executed as `python -I` in a temp working directory with a 10 s
  timeout. Pass means exit code 0. All arms go through the same scoring path.
- Cost accounting: call count, input tokens and output tokens come from the
  usage fields of each API response (`prompt_tokens`, `completion_tokens`) and
  are accumulated per task and arm, so reviewer tokens land in the reviewer
  arm's row. The cost multiplier is average total tokens per task divided by
  the none arm's value. Tokens are the cost proxy; the USD figure in RESULTS.md
  is an estimate from list prices, and a budget guard stops a real run at 80
  percent of a 2 USD cap.
- Determinism: temperature 0, thinking disabled, one run per arm, no repeats.

## Limitations

- One model, glm-4.5-flash, a flash tier. The paper compared 17 verification
  designs across 7 frontier models on Terminal-Bench and SWE-bench Verified;
  this is 4 simplified arms, not ports, on 20 HumanEval function-synthesis
  problems scored pass/fail against bundled tests.
- 20-task subsets: one flipped task moves a pass rate by 5 points, and every
  delta observed is exactly that. Conclusions are sign only, with no repeats
  and no error bars.
- The first-20 subset saturates for this model, so the hard subset was selected
  after observing that saturation.
- The gate arm sees the bundled tests, which rewards fitting those exact
  asserts.
- HumanEval function synthesis is easier and more self-contained than the
  agentic benchmarks where the paper located its findings.

## Citation

The compared designs and the direction hypotheses come from this paper:

```bibtex
@misc{rethinkingverification2026,
  title         = {Rethinking Verification in Agent Harnesses},
  year          = {2026},
  eprint        = {2610.34577},
  archivePrefix = {arXiv},
  url           = {https://arxiv.org/abs/2610.34577}
}
```

This repository:

```bibtex
@misc{verifyharness2026,
  title = {verify-harness},
  year  = {2026},
  note  = {Small benchmark comparing four verification designs for coding
           agents; mini replication of arXiv 2610.34577}
}
```

## Layout

```
run.py                  entry point
src/model.py            API client, usage tracking, mock client
src/tasks.py            HumanEval loading, fallback set, test runner
src/arms.py             the four verification arms
src/report.py           aggregation, results.csv, RESULTS.md
tests/                  pytest suite, no network needed
data/HumanEval.jsonl    cached task set (MIT, openai/human-eval)
results/                per-task CSVs for both measured runs and the mock run
run_output*.txt         raw console logs of the two measured runs
RESULTS.md              measured numbers, regenerated by full runs
DECISIONS.md            every non-obvious implementation choice
```

## License

MIT, see LICENSE. The bundled HumanEval data follows its own MIT license
(https://github.com/openai/human-eval).
