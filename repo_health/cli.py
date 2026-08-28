"""Command-line entry point: `repo-health <path> [options]`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report import build_report, format_text_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-health",
        description=(
            "Score a local git repository's portfolio health: README quality, "
            "real vs. stub implementation, test presence, tutorial-clone "
            "signal, description, and committed-secret scanning."
        ),
    )
    parser.add_argument("path", help="Path to the repository to audit.")
    parser.add_argument(
        "--name",
        help="Repo name to use in the report (defaults to the directory name).",
    )
    parser.add_argument(
        "--description",
        default=None,
        help="The repo's description field, if you want it factored into the score "
        "(e.g. pulled from `git remote` metadata or a hosting API).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full report as JSON instead of a human-readable summary.",
    )
    parser.add_argument(
        "--fail-under",
        type=int,
        default=None,
        metavar="SCORE",
        help="Exit with status 1 if the overall score is below SCORE. "
        "Useful as a CI gate.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_path = Path(args.path)
    if not repo_path.exists() or not repo_path.is_dir():
        print(f"error: '{args.path}' is not a directory", file=sys.stderr)
        return 2

    report = build_report(repo_path, repo_name=args.name, description=args.description)

    if args.json:
        print(report.to_json())
    else:
        print(format_text_report(report))

    if args.fail_under is not None and report.overall_score < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
