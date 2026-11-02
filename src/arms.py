"""The four verification arms. Each returns the final code plus the solver
message history it built; the runner scores the final code with run_tests."""
import re

SOLVER_SYSTEM = (
    "You are an expert Python programmer. Solve the given coding task. "
    "Return the complete solution as a single Python code block. "
    "Include any needed imports. Do not include tests or example usage."
)

SELFCHECK_PROMPT = (
    "Review your own solution against the task. Check correctness carefully, "
    "including edge cases from the docstring examples. Then output the final "
    "version of the solution as a single Python code block. "
    "If your solution was already correct, output it unchanged."
)

REVIEWER_SYSTEM = (
    "You are an independent code reviewer. You did not write this code. "
    "Judge only whether it correctly solves the task."
)

REVIEWER_PROMPT = (
    "Task:\n{prompt}\n\nProposed solution:\n{code}\n\n"
    "Decide whether the solution correctly solves the task, including the "
    "docstring examples and edge cases.\n"
    "Answer with a first line exactly 'VERDICT: APPROVE' or 'VERDICT: REVISE'. "
    "If you choose REVISE, list the concrete problems on the following lines."
)

REVISION_PROMPT = (
    "{source} requests changes to your solution:\n{comments}\n"
    "Return a corrected complete solution as a single Python code block."
)

GATE_PROMPT = (
    "Your solution failed the task tests. Test output:\n{error}\n"
    "Return a corrected complete solution as a single Python code block."
)

FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)
VERDICT_RE = re.compile(r"VERDICT:\s*(APPROVE|REVISE)", re.IGNORECASE)


def extract_code(text):
    """Return the last fenced code block, or the whole text if no fence."""
    blocks = FENCE_RE.findall(text or "")
    if blocks:
        return blocks[-1].strip()
    return (text or "").strip()


def parse_verdict(text):
    """Return (verdict, comments) where verdict is APPROVE or REVISE."""
    match = VERDICT_RE.search(text or "")
    if not match:
        return "REVISE", (text or "").strip()
    verdict = match.group(1).upper()
    rest = (text or "")[match.end():].strip()
    return verdict, rest


def solve(client, task):
    """Base solver call shared by every arm. Returns (messages, code)."""
    messages = [
        {"role": "system", "content": SOLVER_SYSTEM},
        {"role": "user", "content": task["prompt"]},
    ]
    code = extract_code(client.chat(messages))
    return messages, code


def arm_none(client, reviewer, task, run):
    messages, code = solve(client, task)
    return code


def arm_selfcheck(client, reviewer, task, run):
    messages, code = solve(client, task)
    messages = messages + [
        {"role": "assistant", "content": code},
        {"role": "user", "content": SELFCHECK_PROMPT},
    ]
    revised = extract_code(client.chat(messages))
    return revised or code


def arm_reviewer(client, reviewer, task, run):
    messages, code = solve(client, task)
    review = reviewer.chat([
        {"role": "system", "content": REVIEWER_SYSTEM},
        {"role": "user", "content": REVIEWER_PROMPT.format(prompt=task["prompt"], code=code)},
    ])
    verdict, comments = parse_verdict(review)
    if verdict == "APPROVE" or not comments:
        return code
    messages = messages + [
        {"role": "assistant", "content": code},
        {"role": "user", "content": REVISION_PROMPT.format(
            source="An independent reviewer", comments=comments)},
    ]
    revised = extract_code(client.chat(messages))
    return revised or code


def arm_gate(client, reviewer, task, run, max_retries=2):
    messages, code = solve(client, task)
    passed, error = run(task, code)
    retries = 0
    while not passed and retries < max_retries:
        retries += 1
        messages = messages + [
            {"role": "assistant", "content": code},
            {"role": "user", "content": GATE_PROMPT.format(error=error)},
        ]
        code = extract_code(client.chat(messages)) or code
        passed, error = run(task, code)
    return code


ARMS = {
    "none": arm_none,
    "selfcheck": arm_selfcheck,
    "reviewer": arm_reviewer,
    "gate": arm_gate,
}
