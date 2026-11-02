from arms import arm_gate, arm_none, arm_reviewer, arm_selfcheck, extract_code, parse_verdict
from model import MockClient
from tasks import MINI_TASKS


def fake_executor(task, completion):
    """Deterministic stand-in for run_tests: only MOCK_REVISED passes."""
    passed = "MOCK_REVISED" in (completion or "")
    return passed, "" if passed else "assertion error"


TASK = MINI_TASKS[0]


def test_extract_code_prefers_last_fence():
    text = "junk\n```python\ndef a():\n    pass\n```\nmore junk\n```\ndef b():\n    pass\n```"
    assert extract_code(text) == "def b():\n    pass"


def test_extract_code_without_fence_returns_text():
    assert extract_code("x = 1") == "x = 1"


def test_parse_verdict():
    assert parse_verdict("VERDICT: REVISE\n\nCOMMENTS: off by one")[0] == "REVISE"
    assert parse_verdict("first line\nVERDICT: APPROVE")[0] == "APPROVE"
    verdict, _ = parse_verdict("no verdict at all")
    assert verdict == "REVISE"  # unreadable review defaults to requesting a revision


def test_arm_none_single_call():
    client = MockClient()
    code = arm_none(client, MockClient(), TASK, fake_executor)
    assert code == "MOCK_SOLVE"
    assert client.usage.calls == 1


def test_arm_selfcheck_two_calls_same_context():
    client = MockClient()
    code = arm_selfcheck(client, MockClient(), TASK, fake_executor)
    assert code == "MOCK_SELFCHECK"
    assert client.usage.calls == 2


def test_arm_reviewer_three_calls_when_revise():
    client = MockClient()
    reviewer = MockClient()
    code = arm_reviewer(client, reviewer, TASK, fake_executor)
    assert code == "MOCK_REVISED"
    assert client.usage.calls == 2  # solve plus revision
    assert reviewer.usage.calls == 1  # independent review


def test_arm_gate_retries_until_pass():
    client = MockClient()
    code = arm_gate(client, MockClient(), TASK, fake_executor, max_retries=2)
    assert code == "MOCK_REVISED"
    assert client.usage.calls == 2  # solve plus one feedback round


def test_arm_gate_gives_up_after_max_retries():
    def always_fail(task, completion):
        return False, "assertion error"

    client = MockClient()
    code = arm_gate(client, MockClient(), TASK, always_fail, max_retries=2)
    assert client.usage.calls == 3  # solve plus two retries
    assert code == "MOCK_REVISED"
