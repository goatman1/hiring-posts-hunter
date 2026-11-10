# Local helper API

From repository root, with Python 3.12+:

`python .agents/skills/job-search/scripts/job_hunter.py COMMAND --input .local/request.json --data-dir .local`

Write JSON inputs to files; never interpolate collected text into shell commands. Outputs are JSON; errors use stderr and exit code 1.

| Command | Input |
|---|---|
| init | `{}` |
| start-run | `{"config":{"resume_dir":"../resumes","target_count":100}}` |
| run-status | `{"run_id":"..."}` |
| checkpoint | `{"run_id":"...","elapsed_seconds":12,"progress":{"query_index":0},"stop_reason":null}` |
| ingest-posts | `{"run_id":"...","posts":[{"url":"...","author_url":"...","author_name":"...","author_position":"...","content":"...","posted_date":"2d","date_precision":"relative","track":"tech"}]}` |
| save-evidence | `{"post_id":"...","source_url":"...","quote":"exact excerpt"}` |
| analysis-batch | `{"run_id":"...","limit":10,"offset":0}` |
| save-assessments | `{"run_id":"...","assessments":[...]}` |
| list-leads | `{"bucket":"Shortlist","new_only":true,"limit":50}` |
| update-lead | `{"lead_id":"...","edits":{"status":"applied","notes":"..."}}` |
| record-application | `{"lead_id":"...","event_id":"stable-id","details":{"type":"application","url":"..."},"edits":{"status":"applied","application_date":"2027-01-06"}}` |
| sync-workbook | `{}` |

Ingestion returns post IDs; batch output provides content_digest and resume IDs. Copy them exactly. Editable tracking fields: status, notes, next_action, follow_up_date, application_date. Statuses: new, reviewing, shortlisted, saved, contacted, applied, interviewing, offer, rejected, withdrawn, dismissed, closed. Event IDs make history idempotent.

Save bulk inputs in ignored .local. Analysis batches include resume variants: coordinator selects relevant excerpts before delegation. Avoid loading the entire database into context.
