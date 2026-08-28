from pathlib import Path

from repo_health.code_signal import assess_code


def test_no_source_files_is_stub(tmp_path: Path):
    (tmp_path / "README.md").write_text("# empty project\n")
    (tmp_path / "LICENSE").write_text("MIT License\n")

    signal = assess_code(tmp_path)

    assert signal.source_files == 0
    assert signal.is_likely_stub


def test_real_implementation_with_tests(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def add(a, b):\n    return a + b\n" * 20)

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text(
        "from src.main import add\n\ndef test_add():\n    assert add(1, 2) == 3\n"
    )

    signal = assess_code(tmp_path)

    assert signal.source_files == 1
    assert signal.has_tests
    assert not signal.is_likely_stub


def test_tutorial_clone_hint_detected(tmp_path: Path):
    src = tmp_path / "task-manager-backend"
    src.mkdir()
    (src / "server.js").write_text("console.log('crud app');\n" * 20)

    signal = assess_code(tmp_path, repo_name="task-manager-backend")

    assert signal.tutorial_clone_hint == "task-manager"


def test_trivially_small_source_is_stub(tmp_path: Path):
    (tmp_path / "app.py").write_text("pass\n")

    signal = assess_code(tmp_path)

    assert signal.is_likely_stub
