"""Heuristics for scoring README quality.

Goal: catch the two failure modes that make a portfolio repo look
unfinished — no README at all, and an unedited scaffold/template README
(Vite, Create React App, Lovable, cookiecutter, "TODO" placeholders) that
was never actually rewritten to describe the project.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

README_NAMES = ["README.md", "README.rst", "README.txt", "README"]

TEMPLATE_MARKERS = [
    "this template provides a minimal setup",
    "learn react",
    "getting started with create react app",
    "edit this file to get started",
    "welcome to your lovable project",
    "run `npm run dev`",
    "expo prebuild",
    "getting started with expo",
    "this is a default vite",
    "vite + react",
    "npx create-react-app",
    "cookiecutter",
    "yeoman generator",
    "npm start` to run",
]

STRUCTURAL_SECTIONS = [
    re.compile(r"^#{1,3}\s*(usage|getting started|how to run|installation|setup)\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#{1,3}\s*(features?|what (it|this) does|overview)\b", re.IGNORECASE | re.MULTILINE),
]

CODE_BLOCK_PATTERN = re.compile(r"```")

MIN_SUBSTANTIVE_LENGTH = 300


@dataclass
class ReadmeReport:
    exists: bool
    path: str | None = None
    length: int = 0
    looks_like_template: bool = False
    template_markers_found: list[str] = field(default_factory=list)
    has_structural_sections: bool = False
    has_code_block: bool = False
    score: int = 0
    notes: list[str] = field(default_factory=list)


def find_readme(root: str | Path) -> Path | None:
    root = Path(root)
    for name in README_NAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    for child in root.iterdir():
        if child.is_file() and child.name.lower().startswith("readme"):
            return child
    return None


def assess_readme(root: str | Path) -> ReadmeReport:
    path = find_readme(root)
    if path is None:
        return ReadmeReport(exists=False, score=0, notes=["No README file found."])

    text = path.read_text(encoding="utf-8", errors="ignore")
    lower = text.lower()

    markers_found = [m for m in TEMPLATE_MARKERS if m in lower]
    looks_like_template = len(markers_found) >= 1 and len(text) < 1500

    has_sections = any(p.search(text) for p in STRUCTURAL_SECTIONS)
    has_code_block = bool(CODE_BLOCK_PATTERN.search(text))

    score = 0
    notes: list[str] = []

    if len(text) < MIN_SUBSTANTIVE_LENGTH:
        notes.append(f"README is only {len(text)} bytes — likely a stub.")
    else:
        score += 35

    if looks_like_template:
        notes.append(
            "README appears to be unedited scaffold/template text "
            f"(matched: {', '.join(markers_found[:3])})."
        )
    else:
        score += 25

    if has_sections:
        score += 25
    else:
        notes.append("No 'usage'/'setup'/'features' style section headers found.")

    if has_code_block:
        score += 15
    else:
        notes.append("No fenced code block (install/run instructions) found.")

    return ReadmeReport(
        exists=True,
        path=str(path),
        length=len(text),
        looks_like_template=looks_like_template,
        template_markers_found=markers_found,
        has_structural_sections=has_sections,
        has_code_block=has_code_block,
        score=min(score, 100),
        notes=notes,
    )
