"""Aggregate a repo's README, code, and secret signals into one report."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .code_signal import CodeSignal, assess_code
from .readme_quality import ReadmeReport, assess_readme
from .secrets_scan import Finding, ScanResult, scan_path


@dataclass
class RepoReport:
    repo_path: str
    repo_name: str
    description_provided: bool
    readme: ReadmeReport
    code: CodeSignal
    secrets: ScanResult
    overall_score: int = 0
    grade: str = ""
    summary: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def _grade_for(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 50:
        return "C"
    if score >= 30:
        return "D"
    return "F"


def build_report(
    repo_path: str | Path,
    repo_name: str | None = None,
    description: str | None = None,
) -> RepoReport:
    repo_path = Path(repo_path)
    repo_name = repo_name or repo_path.name

    readme = assess_readme(repo_path)
    code = assess_code(repo_path, repo_name=repo_name)
    secrets = scan_path(repo_path)

    description_provided = bool(description and description.strip())

    score = 0
    summary: list[str] = []

    score += round(readme.score * 0.35)

    if code.is_likely_stub:
        summary.append("No real implementation detected (README/stub only).")
    else:
        code_points = 35
        if not code.has_tests:
            code_points -= 10
            summary.append("Has implementation code but no tests.")
        score += code_points

    if description_provided:
        score += 10
    else:
        summary.append("Repository description field is empty.")

    if code.tutorial_clone_hint and not code.is_likely_stub:
        score -= 5
        summary.append(
            f"Reads like a common tutorial-clone pattern ('{code.tutorial_clone_hint}') "
            "— consider what makes this stand out on a resume."
        )

    if not secrets.clean:
        score = min(score, 20)
        summary.append(
            f"{len(secrets.findings)} potential secret(s) found in the current tree — "
            "treat as urgent regardless of other scores."
        )

    score = max(0, min(100, score))

    if not summary:
        summary.append("Looks solid: real code, tests, README, and description all present.")

    return RepoReport(
        repo_path=str(repo_path),
        repo_name=repo_name,
        description_provided=description_provided,
        readme=readme,
        code=code,
        secrets=secrets,
        overall_score=score,
        grade=_grade_for(score),
        summary=summary,
    )


def format_text_report(report: RepoReport) -> str:
    lines = [
        f"Repo: {report.repo_name}",
        f"Overall score: {report.overall_score}/100 (grade {report.grade})",
        "",
        f"README: {'present' if report.readme.exists else 'MISSING'}"
        + (f" ({report.readme.length} bytes, score {report.readme.score}/100)" if report.readme.exists else ""),
        f"Description field: {'set' if report.description_provided else 'EMPTY'}",
        f"Source files: {report.code.source_files} "
        f"({report.code.total_source_bytes} bytes across {len(report.code.languages)} extension(s))",
        f"Tests: {'present (' + str(report.code.test_files) + ' file(s))' if report.code.has_tests else 'NONE FOUND'}",
        f"Secrets scan: {'clean' if report.secrets.clean else str(len(report.secrets.findings)) + ' FINDING(S)'} "
        f"({report.secrets.files_scanned} files scanned)",
        "",
        "Summary:",
    ]
    for line in report.summary:
        lines.append(f"  - {line}")

    if not report.secrets.clean:
        lines.append("")
        lines.append("Secret findings:")
        for finding in report.secrets.findings:
            lines.append(f"  - {finding}")

    return "\n".join(lines)
