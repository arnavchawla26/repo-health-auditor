"""Heuristics for whether a repo contains real implementation, has tests,
and reads as an original project rather than a generic tutorial clone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt",
    ".rb", ".c", ".cpp", ".cs", ".swift", ".php", ".scala", ".m",
}

TEST_HINTS_DIR = {"test", "tests", "__tests__", "spec", "specs"}
TEST_HINTS_FILENAME = ("test_", "_test", ".test.", ".spec.")

IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", "vendor", ".venv", "venv",
    "__pycache__", ".tox", ".next", "coverage",
}

TUTORIAL_CLONE_HINTS = [
    "todo", "task-manager", "taskmanager", "crud-app", "blog-api",
    "shopping-cart", "weather-app", "calculator-app", "counter-app",
]


@dataclass
class CodeSignal:
    source_files: int = 0
    total_source_bytes: int = 0
    test_files: int = 0
    has_tests: bool = False
    languages: dict[str, int] = field(default_factory=dict)
    tutorial_clone_hint: str | None = None
    is_likely_stub: bool = False
    notes: list[str] = field(default_factory=list)


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        yield path


def assess_code(root: str | Path, repo_name: str = "") -> CodeSignal:
    root = Path(root)
    signal = CodeSignal()

    for path in _iter_files(root):
        ext = path.suffix.lower()
        name_lower = path.name.lower()
        rel_parts_lower = [p.lower() for p in path.relative_to(root).parts]

        is_test = (
            any(name_lower.startswith(h) or h in name_lower for h in TEST_HINTS_FILENAME)
            or any(part in TEST_HINTS_DIR for part in rel_parts_lower)
        )

        if ext in SOURCE_EXTENSIONS:
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if is_test:
                signal.test_files += 1
            else:
                signal.source_files += 1
                signal.total_source_bytes += size
                signal.languages[ext] = signal.languages.get(ext, 0) + 1

    signal.has_tests = signal.test_files > 0

    haystack = f"{repo_name} " + " ".join(
        str(p.relative_to(root)) for p in _iter_files(root)
    )
    haystack_lower = haystack.lower()
    for hint in TUTORIAL_CLONE_HINTS:
        if hint in haystack_lower:
            signal.tutorial_clone_hint = hint
            break

    if signal.source_files == 0:
        signal.is_likely_stub = True
        signal.notes.append("No source files found — README/license only, no implementation.")
    elif signal.total_source_bytes < 500 and signal.source_files <= 2:
        signal.is_likely_stub = True
        signal.notes.append("Source present but trivially small — likely a stub or placeholder.")

    if not signal.has_tests and signal.source_files > 0:
        signal.notes.append("No test files detected.")

    if signal.tutorial_clone_hint:
        signal.notes.append(
            f"Repo name/paths match a common tutorial-project pattern "
            f"('{signal.tutorial_clone_hint}') — worth a second look for originality."
        )

    return signal
