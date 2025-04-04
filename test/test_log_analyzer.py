from log_analyzer.log_analyzer import find_last_log


def test_find_log_correct_log(tmpdir):
    file_name = "nginx-access-ui.log-20240101"
    with open(tmpdir / file_name, mode="wb"):
        pass
    last_log = find_last_log(tmpdir)
    assert last_log.file_name == file_name


def test_find_log_dir_has_log_format(tmpdir):
    (tmpdir / "nginx-access-ui.log-20240101").mkdir()
    last_log = find_last_log(tmpdir)
    assert last_log is None


def test_find_log_correct_gz(tmpdir):
    file_name = "nginx-access-ui.log-20240101.gz"
    with open(tmpdir / file_name, mode="wb"):
        pass
    last_log = find_last_log(tmpdir)
    assert last_log.file_name == file_name


def test_find_log_incorrect(tmpdir):
    file_name = "nginx-access-ui.log-20240101123"
    with open(tmpdir / file_name, mode="wb"):
        pass
    last_log = find_last_log(tmpdir)
    assert last_log is None


def test_find_log_incorrect_date(tmpdir):
    file_name = "nginx-access-ui.log-20240631"
    with open(tmpdir / file_name, mode="wb"):
        pass
    last_log = find_last_log(tmpdir)
    assert last_log is None
