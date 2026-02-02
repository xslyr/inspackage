from inspackage.inspection import list_details


def test_inspection_must_construct_tree(console, capsys):
    package_name = "dotenv"
    list_details(console, package_name)
    captured = capsys.readouterr()
    assert package_name in captured.out
    assert "Methods:" in captured.out
