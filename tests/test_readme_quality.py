from pathlib import Path

from repo_health.readme_quality import assess_readme


def test_missing_readme(tmp_path: Path):
    report = assess_readme(tmp_path)
    assert not report.exists
    assert report.score == 0


def test_stub_readme_scores_low(tmp_path: Path):
    (tmp_path / "README.md").write_text("# my-project\n")
    report = assess_readme(tmp_path)
    assert report.exists
    assert report.score < 40


def test_unedited_vite_template_flagged(tmp_path: Path):
    text = (
        "# React + TypeScript + Vite\n\n"
        "This template provides a minimal setup to get React working in Vite "
        "with HMR and some ESLint rules.\n\n"
        "Currently, two official plugins are available.\n"
    )
    (tmp_path / "README.md").write_text(text)
    report = assess_readme(tmp_path)
    assert report.looks_like_template
    assert report.score < 50


def test_substantive_readme_scores_high(tmp_path: Path):
    text = (
        "# widget-tracker\n\n"
        "A small service that tracks widget inventory across warehouses.\n\n"
        "## Features\n"
        "- Real-time stock levels\n"
        "- Low-stock alerts\n\n"
        "## Installation\n"
        "```bash\n"
        "pip install -r requirements.txt\n"
        "```\n\n"
        "## Usage\n"
        "```bash\n"
        "python -m widget_tracker --config config.yaml\n"
        "```\n\n"
        "## Tech stack\n"
        "Python, SQLite, FastAPI.\n" * 3
    )
    (tmp_path / "README.md").write_text(text)
    report = assess_readme(tmp_path)
    assert report.score >= 80
    assert report.has_structural_sections
    assert report.has_code_block
    assert not report.looks_like_template


def test_finds_lowercase_readme(tmp_path: Path):
    (tmp_path / "readme.md").write_text("# lowercase readme\n\nSome real content here that is long enough " * 5)
    report = assess_readme(tmp_path)
    assert report.exists
