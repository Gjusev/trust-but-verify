from report import aggregate, table_md, write_csv


def rows_for(calls_by_arm):
    rows = []
    for arm, calls in calls_by_arm.items():
        rows.append({"task_id": "T/0", "arm": arm, "passed": 1, "calls": calls,
                     "input_tokens": 100 * calls, "output_tokens": 50 * calls})
        rows.append({"task_id": "T/1", "arm": arm, "passed": 0, "calls": calls,
                     "input_tokens": 100 * calls, "output_tokens": 50 * calls})
    return rows


def test_aggregate_math():
    stats = aggregate(rows_for({"none": 1, "reviewer": 3}))
    assert stats["none"]["pass_rate"] == 0.5
    assert stats["reviewer"]["avg_calls"] == 3
    assert stats["reviewer"]["avg_tokens"] == 450
    assert abs(stats["reviewer"]["cost_mult"] - 3.0) < 1e-9
    assert stats["none"]["cost_mult"] == 1.0


def test_table_contains_all_arms():
    stats = aggregate(rows_for({"none": 1, "selfcheck": 2, "reviewer": 3, "gate": 2}))
    table = table_md(stats)
    for arm in ["none", "selfcheck", "reviewer", "gate"]:
        assert arm in table


def test_write_csv_roundtrip(tmp_path):
    rows = rows_for({"none": 1})
    path = write_csv(rows, path=str(tmp_path / "r.csv"))
    content = open(path, encoding="utf-8").read()
    assert content.splitlines()[0] == "task_id,arm,passed,calls,input_tokens,output_tokens"
    assert ",none,1,1,100,50" in content
