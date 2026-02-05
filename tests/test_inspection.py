from inspackage.inspection import get_tree
from inspackage.style import console


def test_inspection_must_construct_tree(capsys):
    package_name = "dotenv"
    tree = get_tree(package_name)
    console.print(tree)
    captured = capsys.readouterr()
    assert package_name in captured.out
    assert "Methods:" in captured.out
