"""Heuristic scanning for likely committed secrets in a file tree.

This is intentionally a *fast, local, dependency-free* heuristic scanner —
it is not a replacement for a dedicated secret-scanning service, but it
catches the common cases that sink a portfolio repo: committed .env files,
hardcoded API keys, private key material, and connection strings with
embedded credentials.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Filenames that are almost always a mistake to commit.
SUSPECT_FILENAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "credentials.json",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

# .env.example / .env.sample / .env.template / .env.dist are the conventional
# *safe* placeholder files (see e.g. dotenv-flow, Rails, Django tooling) and
# must never be flagged just for matching an ".env.*" shape.
SAFE_ENV_SUFFIXES = {"example", "sample", "template", "dist", "test"}

SUSPECT_FILENAME_PATTERNS = [
    re.compile(r".*\.pem$"),
    re.compile(r".*\.pfx$"),
    re.compile(r".*service[-_]?account.*\.json$", re.IGNORECASE),
]


def _is_suspect_dotenv_variant(name: str) -> bool:
    """True for .env.<suffix> files, except the known-safe placeholder suffixes."""
    if not name.startswith(".env."):
        return False
    suffix = name[len(".env."):].lower()
    return suffix not in SAFE_ENV_SUFFIXES

# Content patterns keyed by a human-readable label. Kept intentionally
# specific (prefixed tokens, connection-string shapes) to hold down false
# positives from library source code that merely mentions "token" or "key".
CONTENT_PATTERNS: dict[str, re.Pattern[str]] = {
    "AWS Access Key ID": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "AWS Secret Access Key (assignment)": re.compile(
        r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?"
    ),
    "Generic private key block": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "Stripe secret key": re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    "Generic connection string with credentials": re.compile(
        r"(?i)(mongodb(\+srv)?|postgres(ql)?|mysql|redis)://[^\s:/]+:[^\s@/]+@"
    ),
    "JWT-looking secret assignment": re.compile(
        r"(?i)(jwt|api)[_-]?(secret|key)\s*[=:]\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]"
    ),
}

# Paths that are noise even if they match a content pattern (vendored deps,
# lockfiles, minified bundles, the scanner's own test fixtures).
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
}

MAX_FILE_BYTES = 2_000_000  # skip huge/binary-ish files


@dataclass
class Finding:
    path: str
    reason: str
    line: int | None = None
    snippet: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        loc = f":{self.line}" if self.line else ""
        return f"{self.path}{loc} — {self.reason}"


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def clean(self) -> bool:
        return not self.findings


def _is_probably_text(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return False
    return True


def _iter_files(root: Path, exclude_dirs: set[str]):
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in exclude_dirs for part in path.parts):
            continue
        yield path


def scan_path(root: str | Path, exclude_dirs: set[str] | None = None) -> ScanResult:
    """Recursively scan `root` for suspicious filenames and content patterns."""
    root = Path(root)
    exclude_dirs = exclude_dirs if exclude_dirs is not None else DEFAULT_EXCLUDE_DIRS
    result = ScanResult()

    for path in _iter_files(root, exclude_dirs):
        result.files_scanned += 1
        rel = str(path.relative_to(root))
        name = path.name

        if (
            name in SUSPECT_FILENAMES
            or any(p.match(name) for p in SUSPECT_FILENAME_PATTERNS)
            or _is_suspect_dotenv_variant(name)
        ):
            result.findings.append(Finding(path=rel, reason=f"suspicious filename: {name}"))
            # Still worth scanning content too, so fall through.

        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size == 0 or size > MAX_FILE_BYTES:
            continue

        try:
            data = path.read_bytes()
        except OSError:
            continue
        if not _is_probably_text(data):
            continue

        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            continue

        for label, pattern in CONTENT_PATTERNS.items():
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                snippet = match.group(0)
                if len(snippet) > 60:
                    snippet = snippet[:57] + "..."
                result.findings.append(
                    Finding(path=rel, reason=label, line=line_no, snippet=snippet)
                )

    return result
