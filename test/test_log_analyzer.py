from log_analyzer.log_analyzer import find_last_log


def test_find_log():
    last_log = find_last_log(".")
    assert last_log is None
