import json
import subprocess
import sys
from pathlib import Path


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "repo_health.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )


def test_cli_reports_missing_directory():
    result = _run_cli("/definitely/does/not/exist")
    assert result.returncode == 2
    assert "error" in result.stderr.lower()


def test_cli_text_output(tmp_path: Path):
    (tmp_path / "README.md").write_text("# demo\n\nreal content " * 30)
    (tmp_path / "main.py").write_text("def f():\n    return 1\n" * 20)

    result = _run_cli(str(tmp_path))

    assert result.returncode == 0
    assert "Overall score" in result.stdout


def test_cli_json_output_is_valid_json(tmp_path: Path):
    (tmp_path / "README.md").write_text("# demo\n\nreal content " * 30)
    (tmp_path / "main.py").write_text("def f():\n    return 1\n" * 20)

    result = _run_cli(str(tmp_path), "--json")

    payload = json.loads(result.stdout)
    assert "overall_score" in payload
    assert payload["repo_name"] == tmp_path.name


def test_cli_fail_under_gates_exit_code(tmp_path: Path):
    (tmp_path / "README.md").write_text("# empty\n")

    result = _run_cli(str(tmp_path), "--fail-under", "90")

    assert result.returncode == 1
