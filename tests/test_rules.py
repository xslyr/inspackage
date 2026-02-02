import pytest

from inspackage.rules import check_file, check_path


@pytest.mark.parametrize(
    "filename, expectation",
    [
        ("test.py", True),
        (".test.py", False),
        ("_test.py", False),
        ("test.sh", False),
        ("/test.py", True),
        ("/.test.py", False),
        ("/_test.py", False),
        ("/test.sh", False),
    ],
)
def test_rules_check_file_can_validade_all_scenario(filename, expectation):
    result = check_file(filename)
    assert result == expectation


@pytest.mark.parametrize(
    "pathname, expectation",
    [
        ("/home/", True),
        ("/.home/", False),
        ("/_home/", False),
        ("/home", True),
        ("/.home", False),
        ("/_home", False),
    ],
)
def test_rules_check_path_can_validade_all_scenario(pathname, expectation):
    result = check_path(pathname)
    assert result == expectation
