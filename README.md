# repo-health-auditor

A small, dependency-free CLI that scores a local git repository's
"portfolio health" — the same kind of pass you'd do by hand before putting
a project on a resume or GitHub profile: does it have a real README, does
it contain actual working code (not just a license and a promise), does it
have tests, is the description filled in, and does the current tree have
any committed secrets.

It grew out of a recurring manual audit of my own GitHub repos and turned
into a small reusable tool instead of a one-off script.

## What it checks

| Signal | How |
| --- | --- |
| README quality | Finds `README.md`/`README.rst`/etc., flags missing/stub READMEs, and detects unedited scaffold text (Vite, CRA, Lovable, cookiecutter boilerplate that nobody rewrote) |
| Real vs. stub implementation | Counts actual source files/bytes by extension; a repo with only a `LICENSE` and a `README` promising a feature is flagged as a stub |
| Tests | Detects test files by common naming/directory conventions (`tests/`, `test_*.py`, `*.spec.ts`, etc.) |
| Description | Whether a description string was supplied (pass it in from whatever host — GitHub API, GitLab, etc.) |
| Tutorial-clone signal | Flags repo names/paths that match extremely common beginner-project patterns (`todo`, `task-manager`, `crud-app`, ...) as worth a second look |
| Committed secrets | Regex-based scan for `.env` files, private key blocks, AWS/GitHub/Slack/Stripe/Google key shapes, and connection strings with embedded credentials — any finding hard-caps the overall score, since a leaked credential matters more than a missing bullet point in a README |

Everything runs against files already on disk — it doesn't shell out to
`git`, doesn't need a GitHub token, and doesn't send anything over the
network. Clone (or already have) a repo locally and point the tool at it.

## Installation

```bash
git clone https://github.com/arnavchawla26/repo-health-auditor.git
cd repo-health-auditor
pip install -e .
```

Python 3.9+, no runtime dependencies (pytest is dev-only, for running the
test suite).

## Usage

```bash
repo-health /path/to/some/repo
```

```
Repo: widget-tracker
Overall score: 82/100 (grade B)

README: present (1840 bytes, score 90/100)
Description field: set
Source files: 14 (9820 bytes across 2 extension(s))
Tests: present (4 file(s))
Secrets scan: clean (31 files scanned)

Summary:
  - Looks solid: real code, tests, README, and description all present.
```

Pass a description string (e.g. pulled from a hosting API) so it's
factored into the score:

```bash
repo-health /path/to/repo --description "Real-time widget inventory tracker"
```

Get the full structured report as JSON (handy for scripting a batch audit
across many repos, or wiring into CI):

```bash
repo-health /path/to/repo --json
```

Use it as a CI gate — fail the build if a repo's score drops below a
threshold:

```bash
repo-health . --fail-under 60
```

### Note on running it against *this* repo

Running `repo-health .` inside this repo's own checkout will report
several "secret findings" — that's expected and correct: `tests/test_secrets_scan.py`
deliberately contains fake AWS keys, a fake private key block, and a fake
Mongo connection string as test fixtures for the secret scanner itself.
It's a good demonstration that the detector actually works, not a real
leak.

## Library usage

The CLI is a thin wrapper around a plain Python API:

```python
from repo_health.report import build_report, format_text_report

report = build_report("/path/to/repo", description="A thing that does stuff")
print(format_text_report(report))
print(report.overall_score, report.grade)
```

`report.secrets`, `report.readme`, and `report.code` expose the individual
sub-reports if you want finer-grained signals than the rolled-up score.

## Scoring model

The overall score (0–100) weights:

- README quality — up to 35 points (length, structural sections, a code
  block, and a penalty for unedited template text)
- Real implementation — up to 35 points, minus 10 if there's code but no
  tests, and 0 entirely if there's no real implementation at all
- Description filled in — 10 points
- Tutorial-clone pattern match — small penalty, not disqualifying
- **Any committed-secret finding hard-caps the score at 20**, regardless of
  everything else — a leaked credential is a different category of problem
  than a thin README

Grades: A (85+), B (70+), C (50+), D (30+), F (below 30).

## Running the tests

```bash
pip install -e ".[dev]"  # or: pip install pytest -e .
pytest
```

24 tests covering the secret scanner (including that `.env.example` /
`.env.sample` placeholder files are correctly *not* flagged), README
heuristics, code-signal detection, the aggregate scorer, and the CLI
itself (subprocess-level, including `--json` and `--fail-under`).

## Why this exists

Auditing your own GitHub profile by hand — is this description filled in,
does that README actually explain anything, is this repo secretly leaking
a database password — doesn't scale past a handful of repos, and it's
exactly the kind of checklist a small script does better than a human
skimming a page. This is that script, generalized enough to run on any
local repo, not just mine.
