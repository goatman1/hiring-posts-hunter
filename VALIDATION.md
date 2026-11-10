# Validation

Implementation tested on the existing Codex Python 3.12.14 runtime with Pydantic, openpyxl, and pypdf. No browser or model dependency was installed. Run `python -m unittest discover -s tests -v` from the repository root.

All 17 synthetic tests passed. They cover 30-post ingestion, reruns and persistence reopening, bounded batches, verification routing, repeated assessments, multiple roles, edited-post invalidation, unsupported resume quotes/drafts, confirmed requisition grouping, application event idempotence, spreadsheet text safety and edit import, conflicting edits, rollback, URL variants, locked exports, time/no-progress limits, and DOCX/PDF pairing. A local helper run also loaded all five existing resume variants successfully.

## Live check — November 10, 2026

Codex's existing Chrome connection accessed an authenticated LinkedIn Posts search. Latest and Past week were visibly selected. Nine post cards were available. Attempting further loading exposed: “Could not connect to the reCAPTCHA service. Please check your internet connection and reload to get a reCAPTCHA challenge.” Browser work stopped at that boundary.

The 30-candidate end-to-end smoke test, loading beyond 15 posts, and ten-assessment live audit are **incomplete**. No claim of live matching accuracy or complete collection is made. A user-resolved browser session is needed to finish those acceptance checks. No messages or applications were sent.

Classification semantics and draft truthfulness require Codex review: structural validation and saved evidence IDs cannot independently establish that a source supports a conclusion. Synthetic tests verify routing and provenance, not real-world precision.
