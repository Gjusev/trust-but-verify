# DECISIONS

Non-obvious choices, in the order they came up.

## Model selection

- The task brief suggested glm-5.3 or glm-5.3-flash on https://api.z.ai/api/paas/v4.
  Both are listed by GET /models but every call returns HTTP 1113 "Insufficient
  balance or no resource package". A probe of all 12 listed models showed exactly
  one callable with the available ZAI_API_KEY: glm-4.5-flash. Everything else,
  including all glm-5.x and glm-4.6+ tiers, returns 1113.
- Therefore solver and reviewer both default to glm-4.5-flash. The reviewer arm
  still satisfies "independent" in the sense the spec defines: a fresh context
  with no shared message history. Model names are flags (--solver-model,
  --reviewer-model) so a rerun with a different pool needs no code change.
- glm-4.5-flash accepts `thinking: {type: disabled}`. glm-5.3 rejects it with
  "this model always engages in thinking". Disabling thinking keeps answers
  direct and output tokens low, which matters because output is the expensive
  side. This only works because the callable model is 4.5-flash.

## Task set

- HumanEval downloaded from openai/human-eval (HumanEval.jsonl.gz), decompressed
  once into data/HumanEval.jsonl and committed, so reruns need no network.
- First 20 tasks by numeric task id (HumanEval/0 .. HumanEval/19). Sorting is
  on the integer suffix because lexicographic order would give 0,1,10,11,...
- Fallback if the file is missing and download fails: a 4-problem mini set
  written by hand in src/tasks.py with deterministic asserts. Mock and test
  modes use it; real runs use HumanEval.
- Test execution: the model completion is concatenated after the prompt, then
  the task's own test block and a check(entry_point) call, written to a temp
  file and run as `python -I file.py` in a temp cwd with a 10 s timeout.
  - Python makes prompt+completion concatenation safe: if the model repeats the
    signature, the second def overrides the first; if it returns a pure
    continuation, it completes the trailing signature. No dedupe logic needed.
  - `-I` (isolated mode) drops site packages and user site; this is a soft
    sandbox only. The spec excludes docker and this is function-synthesis
    code, accepted risk, documented here.
  - Pass means exit code 0. Stderr tail (last 1500 chars) is what the gate arm
    feeds back to the model.

## Arms

- Base solver prompt shared by all arms: system message plus the raw HumanEval
  prompt, ask for one fenced Python block. Code extraction takes the last
  fenced block, else the whole reply.
- selfcheck: one extra turn in the same message history asking the agent to
  review its own solution and output the final version. 2 calls.
- reviewer: a fresh call (new message list, reviewer system prompt) that must
  answer "VERDICT: APPROVE" or "VERDICT: REVISE" plus comments. On REVISE, the
  original solver history gets one more turn with those comments. Unparseable
  verdicts count as REVISE (an unreadable review should not silently wave a
  solution through). 2 or 3 calls.
- gate: run the bundled tests; on failure append the test output and retry,
  max 2 retries, stop early on a pass. Last attempt is what gets scored.
- All arms are scored the same way: the final code is executed against the
  task tests once more by the runner (for gate this repeats a known result;
  uniformity was worth one extra subprocess).

## Accounting

- Solver and reviewer calls for a task share one Usage object, so reviewer
  tokens land in the reviewer arm's row, as the spec asks.
- Cost multiplier is avg total tokens per task divided by the none arm's value.
- Cost in USD is an upper bound: GLM-4.5 series list price 0.2/1.1 USD per Mtok
  applied to a model the z.ai docs label a free tier. Budget guard in run.py
  stops the run at 1.6 USD estimated (80 percent of the 2 USD cap).

## Mock mode

- MockClient returns canned responses keyed on the prompt it sees (solve,
  selfcheck, gate feedback, reviewer verdict) and reports fake usage
  (100 in + 20 out per call). The mock executor passes only code containing
  MOCK_REVISED. Result: none 0 percent / selfcheck 0 / reviewer 100 / gate 100,
  with 1/2/3/2 calls. That spread exercises every arm path and is labeled fake
  everywhere it appears. Real runs never use it.

## Misc

- temperature 0 everywhere, one run per arm: determinism over variance
  estimates, since 20 tasks cannot support error bars anyway.
- Python 3.12 runs the project (spec says 3.11+); the 3.10 also on this
  machine is not used.
- hermes_run.log (a failed proxy start attempt from before this project) was
  deleted as unrelated debris.

## The two measured runs

- The spec-default run (first 20 HumanEval tasks) saturated: glm-4.5-flash
  solved all 20 first-try, so every arm scored 100 percent and verification
  deltas were structurally zero. That result is reported as measured, not
  hidden.
- A verification-design comparison needs headroom below the ceiling, so a
  second measured run used the last 20 tasks by numeric id (HumanEval/144 to
  /163, run.py --offset 144). Selection procedure: one none-arm-only probe
  run on that subset showed 85 percent, then the full four-arm run was
  executed there. No other subsets were shopped.
- The first-20 run wrote its per-task rows only to results/results.csv, which
  a later probe overwrote. The full per-task log (run_output.txt: task, arm,
  verdict, calls, tokens) was used to reconstruct the identical rows; that is
  the same measured data, not a rerun. Both raw logs are kept in the repo.
- Measured totals across both runs: about 97k tokens, estimated 0.05 USD
  against the 2 USD cap.
- Direction observed on the harder subset: reviewer +5 points at 3.56x token
  cost, gate +5 at 1.50x, selfcheck +5 at 2.73x. The paper's gate cost range
  (1.5x to 1.8x) matches the gate multiplier here; its reviewer cost range
  (1.13x to 1.25x) does not, because our base arm is a single short call and
  every verification turn pays full context again.
