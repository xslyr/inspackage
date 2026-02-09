from inspackage._inspection import get_tree_map


def test_inspection_must_construct_tree(capsys):
    package_name = "dotenv"
    tree = get_tree_map(package_name)
    assert tree["name"] == package_name
