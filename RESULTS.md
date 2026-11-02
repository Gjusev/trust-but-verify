# RESULTS

STATUS: MEASURED. Numbers below come from runs recorded in results/
on this repository.
Run date: 2026-11-02. solver model: glm-4.5-flash, reviewer model: glm-4.5-flash, temperature 0, thinking disabled.

## Run 1: first 20 HumanEval tasks (HumanEval/0 to /19)

Tasks: HumanEval sorted by numeric task id, first 20. Raw log: run_output.txt, per-task rows: results/results_first20.csv. This is the spec-default subset.

| arm | pass rate | avg calls/task | avg tokens/task | cost mult vs none |
|---|---|---|---|---|
| none | 100.0% (20/20) | 1.00 | 285 | 1.00 |
| selfcheck | 100.0% (20/20) | 2.00 | 769 | 2.70 |
| reviewer | 100.0% (20/20) | 2.00 | 660 | 2.32 |
| gate | 100.0% (20/20) | 1.00 | 284 | 1.00 |

## Run 2: last 20 HumanEval tasks (HumanEval/144 to /163)

Tasks: HumanEval sorted by numeric task id, tasks 144 to 163. Chosen after Run 1 saturated (all arms 100 percent, zero headroom). Raw log: run_output_hard.txt, per-task rows: results/results_hard20.csv. Selected with a single-arm probe (none arm only) that showed 85 percent before the four-arm run.

| arm | pass rate | avg calls/task | avg tokens/task | cost mult vs none |
|---|---|---|---|---|
| none | 85.0% (17/20) | 1.00 | 325 | 1.00 |
| selfcheck | 90.0% (18/20) | 2.00 | 887 | 2.73 |
| reviewer | 90.0% (18/20) | 2.15 | 1155 | 3.56 |
| gate | 90.0% (18/20) | 1.25 | 487 | 1.50 |

Total tokens across all measured runs above: 97044. Estimated cost: 0.0519 USD (upper bound, glm-4.5 series list price 0.2/1.1 USD per Mtok; the docs label glm-4.5-flash a free tier). Budget cap: 2 USD.

## Does the direction match the paper

On the subset with headroom below the ceiling, the reviewer arm changed the pass rate by +5.0 points at 3.56x the token cost of the none arm, the gate arm by +5.0 points at 1.50x, and the selfcheck arm by +5.0 points at 2.73x. The paper (arXiv 2610.34577) reports an independent reviewer adding 5.9 to 9.5 points at 1.13x to 1.25x cost and rejection gates adding about 6 points at 1.5x to 1.8x, and advises against completion-time self-checking. Each task here is 5 points, so these numbers carry the sign of the effect at best, not its size.

## Limitations

- 20 HumanEval problems per subset: one flipped task moves a pass rate by 5 points.
- One model (a flash tier), one temperature (0), one run per arm: no error bars.
- HumanEval is function synthesis from docstrings, far easier and more self-contained than Terminal-Bench or SWE-bench Verified, where the paper located its findings.
- The first-20 subset saturates for this model, so verification deltas there are structurally zero; the harder subset was selected after observing that saturation.
- The gate arm sees the bundled tests, which rewards fitting those exact asserts.
- Token counts proxy cost; the price conversion is an estimate, not an invoice.

Compared designs are from Rethinking Verification in Agent Harnesses, arXiv 2610.34577 (https://arxiv.org/abs/2610.34577). This repository is a small independent check of the direction of those findings, not a reproduction.
