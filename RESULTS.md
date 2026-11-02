# RESULTS

STATUS: MOCK RUN. All numbers below come from the deterministic fake
solver and fake test verdicts. They validate plumbing only and are NOT
measurements of any model. Real tables: PENDING.
Run date: 2026-11-02. Tasks: 20 HumanEval problems (first 20 by numeric task id). model: mock (no API calls).

| arm | pass rate | avg calls/task | avg tokens/task | cost mult vs none |
|---|---|---|---|---|
| none | 0.0% (0/20) | 1.00 | 120 | 1.00 |
| selfcheck | 0.0% (0/20) | 2.00 | 240 | 2.00 |
| reviewer | 100.0% (20/20) | 3.00 | 360 | 3.00 |
| gate | 100.0% (20/20) | 2.00 | 240 | 2.00 |

Total tokens across the run: 19200. Estimated cost: 0.0067 USD (upper bound, glm-4.5 series list price 0.2/1.1 USD per Mtok; the docs label glm-4.5-flash a free tier). Budget cap: 2 USD.

## Does the direction match the paper

At this scale the reviewer arm changed the pass rate by +100.0 points at 3.00x the token cost of the none arm, the gate arm by +100.0 points at 2.00x, and the selfcheck arm by +0.0 points. The paper (arXiv 2610.34577) reports an independent reviewer adding 5.9 to 9.5 points at 1.13x to 1.25x cost and rejection gates adding about 6 points at 1.5x to 1.8x, and advises against completion-time self-checking. Whether these tiny-scale deltas agree in sign with those ranges is readable directly from the table above; with 20 tasks each task is 5 points, so any comparison is directional at best.

## Limitations

- 20 HumanEval problems only: one flipped task moves the pass rate by 5 points.
- One model (a flash tier), one temperature (0), one run per arm: no error bars.
- HumanEval is function synthesis from docstrings, far easier and more self-contained than Terminal-Bench or SWE-bench Verified, where the paper located its findings.
- The gate arm sees the bundled tests, which rewards fitting those exact asserts.
- Token counts proxy cost; the price conversion is an estimate, not an invoice.

Compared designs are from Rethinking Verification in Agent Harnesses, arXiv 2610.34577 (https://arxiv.org/abs/2610.34577). This repository is a small independent check of the direction of those findings, not a reproduction.
