from tasks import MINI_TASKS, build_program, load_tasks, run_tests


def test_mini_tasks_load_and_are_few():
    tasks = load_tasks(3, source="mini")
    assert len(tasks) == 3
    assert all("task_id" in t and "test" in t for t in tasks)


def test_run_tests_accepts_correct_completion():
    task = MINI_TASKS[0]
    passed, err = run_tests(task, "    return a + b")
    assert passed, err


def test_run_tests_rejects_wrong_completion():
    task = MINI_TASKS[0]
    passed, _ = run_tests(task, "    return a - b")
    assert not passed


def test_run_tests_rejects_empty_completion():
    assert not run_tests(MINI_TASKS[0], "   ")[0]


def test_run_tests_rejects_infinite_loop():
    task = dict(MINI_TASKS[0])
    passed, err = run_tests(task, "    while True:\n        pass", timeout=3)
    assert not passed
    assert err == "timeout"


def test_run_tests_accepts_full_function_completion():
    """A completion that repeats the signature must still work."""
    task = MINI_TASKS[1]
    completion = "def is_even(n: int) -> bool:\n    return n % 2 == 0\n"
    passed, err = run_tests(task, completion)
    assert passed, err


def test_build_program_contains_check_call():
    program = build_program(MINI_TASKS[0], "    return a + b")
    assert "check(add)" in program


def test_humaneval_subset_is_deterministic():
    tasks = load_tasks(5, source="humaneval")
    if len(tasks) == 5:
        assert [t["task_id"] for t in tasks] == [f"HumanEval/{i}" for i in range(5)]
