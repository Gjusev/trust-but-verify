"""HumanEval task loading and sandboxed test execution."""
import gzip
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

HUMANEVAL_URL = "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz"
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "HumanEval.jsonl")

# Fallback used only when the dataset file is missing and download is blocked.
# Written by hand, deterministic tests, same schema as HumanEval.
MINI_TASKS = [
    {
        "task_id": "Mini/0",
        "prompt": "def add(a: int, b: int) -> int:\n    \"\"\"Return the sum of two integers.\"\"\"\n",
        "entry_point": "add",
        "canonical_solution": "    return a + b",
        "test": "def check(candidate):\n    assert candidate(2, 3) == 5\n    assert candidate(-1, 1) == 0\n",
    },
    {
        "task_id": "Mini/1",
        "prompt": "def is_even(n: int) -> bool:\n    \"\"\"Return True when n is even.\"\"\"\n",
        "entry_point": "is_even",
        "canonical_solution": "    return n % 2 == 0",
        "test": "def check(candidate):\n    assert candidate(4) is True\n    assert candidate(7) is False\n    assert candidate(0) is True\n",
    },
    {
        "task_id": "Mini/2",
        "prompt": "def count_vowels(s: str) -> int:\n    \"\"\"Count vowels in s, case insensitive.\"\"\"\n",
        "entry_point": "count_vowels",
        "canonical_solution": "    return sum(1 for c in s.lower() if c in 'aeiou')",
        "test": "def check(candidate):\n    assert candidate('Hello') == 2\n    assert candidate('xyz') == 0\n    assert candidate('AEIOU') == 5\n",
    },
    {
        "task_id": "Mini/3",
        "prompt": "def max_of_three(a: int, b: int, c: int) -> int:\n    \"\"\"Return the largest of three integers.\"\"\"\n",
        "entry_point": "max_of_three",
        "canonical_solution": "    return max(a, b, c)",
        "test": "def check(candidate):\n    assert candidate(1, 2, 3) == 3\n    assert candidate(5, 5, 2) == 5\n    assert candidate(-1, -2, -3) == -1\n",
    },
]


def _download():
    tmp = DATA_PATH + ".gz"
    urllib.request.urlretrieve(HUMANEVAL_URL, tmp)
    text = gzip.open(tmp, "rb").read().decode("utf-8")
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.remove(tmp)


def load_tasks(limit, source="humaneval"):
    """Return `limit` tasks, deterministically ordered.

    source="humaneval": first `limit` HumanEval tasks by numeric task id
    (cached in data/, downloaded on first use, mini fallback set on failure).
    source="mini": bundled fallback set.
    """
    if source == "mini":
        return MINI_TASKS[:limit]
    if not os.path.exists(DATA_PATH):
        try:
            _download()
        except Exception:
            return MINI_TASKS[:limit]
    with open(DATA_PATH, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    rows.sort(key=lambda r: int(r["task_id"].split("/")[-1]))
    return rows[:limit]


def build_program(task, completion):
    """Assemble the executable program. Appending a full function to the prompt
    is safe in Python: a repeated def simply overrides the earlier one, and a
    continuation style completion completes the trailing signature."""
    return (
        task["prompt"]
        + "\n"
        + completion
        + "\n\n"
        + task["test"]
        + f"\n\ncheck({task['entry_point']})\n"
    )


def run_tests(task, completion, timeout=10):
    """Run the canonical HumanEval check in an isolated subprocess.

    Returns (passed, error_text). passed is True only when the process exits 0.
    """
    if not completion or not completion.strip():
        return False, "empty completion"
    program = build_program(task, completion)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "prog.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(program)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return False, "timeout"
        if proc.returncode == 0:
            return True, ""
        err = (proc.stderr or proc.stdout or "").strip()
        return False, err[-1500:]
