from pathlib import Path

from repo_health.report import build_report, format_text_report


def _make_solid_repo(tmp_path: Path):
    (tmp_path / "README.md").write_text(
        "# solid-project\n\nDoes something genuinely useful.\n\n"
        "## Features\n- thing one\n- thing two\n\n"
        "## Installation\n```bash\npip install -r requirements.txt\n```\n\n"
        "## Usage\n```bash\npython -m solid_project\n```\n" * 2
    )
    src = tmp_path / "solid_project"
    src.mkdir()
    (src / "core.py").write_text("def run():\n    return 42\n" * 30)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_core.py").write_text(
        "from solid_project.core import run\n\ndef test_run():\n    assert run() == 42\n"
    )
    return tmp_path


def test_solid_repo_scores_well(tmp_path: Path):
    _make_solid_repo(tmp_path)
    report = build_report(tmp_path, repo_name="solid-project", description="Does something useful.")

    assert report.overall_score >= 70
    assert report.grade in {"A", "B"}
    assert report.secrets.clean


def test_secret_finding_hard_caps_score(tmp_path: Path):
    _make_solid_repo(tmp_path)
    (tmp_path / ".env").write_text("MONGO_URI=mongodb+srv://admin:leaked@cluster.mongodb.net/prod\n")

    report = build_report(tmp_path, repo_name="solid-project", description="Does something useful.")

    assert report.overall_score <= 20
    assert report.grade == "F"
    assert not report.secrets.clean


def test_stub_repo_scores_poorly(tmp_path: Path):
    (tmp_path / "README.md").write_text(
        "# my-idea\n\nGoing to build a full trading backtester with a "
        "grid-search optimizer and Sharpe/CAGR metrics eventually.\n"
    )
    (tmp_path / "LICENSE").write_text("MIT\n")

    report = build_report(tmp_path, repo_name="my-idea", description=None)

    assert report.overall_score < 50
    assert any("no real implementation" in s.lower() for s in report.summary)


def test_format_text_report_contains_key_fields(tmp_path: Path):
    _make_solid_repo(tmp_path)
    report = build_report(tmp_path, repo_name="solid-project", description="desc")
    text = format_text_report(report)

    assert "solid-project" in text
    assert "Overall score" in text
    assert "Secrets scan: clean" in text
