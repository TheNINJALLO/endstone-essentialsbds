from pathlib import Path
import tomllib


def test_endstone_distribution_name_matches_entry_point():
    pyproject_path = Path(__file__).parents[1] / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)["project"]

    entry_points = project["entry-points"]["endstone"]
    assert len(entry_points) == 1
    entry_point_name = next(iter(entry_points))
    assert project["name"] == f"endstone-{entry_point_name.replace('_', '-')}"


def test_release_version_is_3_5_2():
    pyproject_path = Path(__file__).parents[1] / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)["project"]

    assert project["version"] == "3.5.2"
