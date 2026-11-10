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

Ingestion returns post IDs; batch output provides content_digest and resume IDs. Copy them exactly. Optional ingestion fields: `batch_id` (unique within run, identical retries are idempotent) and `loading_actions` (nonnegative integer, default 1). A repeated batch ID with changed input is rejected. Recovered pending posts are available for analysis but do not count as new. Lexically similar posts are flagged, never automatically merged. Fallback captures can acquire a permalink while retaining stable internal IDs.

Editable tracking fields: status, notes, next_action, follow_up_date, application_date, selected_resume. The assessment's resume is immutable evidence; selected_resume records the user's application choice. Statuses: new, reviewing, shortlisted, saved, contacted, applied, interviewing, offer, rejected, withdrawn, dismissed, closed. Event IDs make history idempotent; replay does not revert a later tracking status. Post and assessment versions retain previous evidence when content changes.

`analysis-batch` offsets refer to the current pending list. Obtain all disjoint worker batches before accepting any submissions, or fetch offset zero after a batch completes. Do not increment offsets across a shrinking list. Checkpoint elapsed_seconds is an increment, not a total; do not replay it after a successful response.

Save bulk inputs in ignored .local. Analysis batches include resume variants: coordinator selects relevant excerpts before delegation. Avoid loading the entire database into context.
