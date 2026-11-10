# Codex Job Hunter

A repository-local Codex skill for US early-career tech/quant hiring-post discovery, resume matching, and application tracking. Codex uses its existing browser tools and reasoning. Local helpers maintain SQLite and Excel; they make no network or model calls.

## Setup

Open this repository as your Codex project. Use Python 3.12+ with Pydantic 2, openpyxl 3, and pypdf 5 or 6 (versions in pyproject.toml). No custom MCP, separate Chromium, or API key is required.

```powershell
python -m pip install "pydantic>=2.11,<3" "openpyxl>=3.1,<4" "pypdf>=5,<7"
Copy-Item config.example.json config.local.json
python .agents/skills/job-search/scripts/job_hunter.py init
```

Set resume_dir in private config.local.json. The default ../resumes points to the existing sibling folder. Use the same supported Python interpreter for all commands. Existing Codex browser access and normal LinkedIn login are prerequisites for discovery.

## Use

> $job-search Find 100 new tech and quant hiring posts from the past week and update my tracker.

Also ask to review shortlisted roles, prepare application answers, record actual application/contact activity, or show pending follow-ups. Follow-up dates are tracking records, not scheduled notifications. The workflow drafts but does not submit, upload, or send.

The skill lives in .agents/skills/job-search; references/commands.md documents helper JSON interfaces. Outputs live in ignored .local. Excel tabs: Shortlist, Needs Review, Candidates, Excluded, Applications, Runs. Edit tracking fields only; ask Codex to sync before regeneration. Conflicting edits require review. Previously contacted/applied/dismissed leads do not resurface as new.

Defaults: latest first, past week, 100 new candidates, 500 inspected posts, 50 loads, 30 active collection minutes, three loads without progress. Unknown author/company/team facts go to Needs Review. Start date and sponsorship are advisory. Scores rank supported fit, not interview probability.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use synthetic fixtures and temporary databases. See VALIDATION.md for actual automated and live results. LinkedIn's website automation restrictions still apply when using an existing browser. The separate hack-job-market repository is not used or modified.
