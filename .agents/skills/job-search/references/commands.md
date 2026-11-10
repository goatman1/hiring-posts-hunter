# Local helper API

From repository root, with Python 3.12+:

`python .agents/skills/job-search/scripts/job_hunter.py COMMAND --input .local/request.json --data-dir .local`

Write JSON inputs to files; never interpolate collected text into shell commands. Outputs are JSON; errors use stderr and exit code 1.

| Command | Input |
|---|---|
| init | `{}` |
| start-run | `{"config":{"resume_dir":"../resumes","target_count":100}}` |
| run-status | `{"run_id":"..."}` |
| feed-audit | `{"run_id":"...","limit":50,"offset":0}` |
| ingest-feed | See feed batch schema below; use only with collection_source=for_you. |
| checkpoint | `{"run_id":"...","elapsed_seconds":12,"progress":{"query_index":0},"stop_reason":null}` |
| ingest-posts | `{"run_id":"...","posts":[{"url":"...","author_url":"...","author_name":"...","author_position":"...","content":"...","posted_date":"2d","date_precision":"relative","track":"tech"}]}` |
| save-evidence | `{"post_id":"...","source_url":"...","quote":"exact excerpt"}` |
| analysis-batch | `{"run_id":"...","limit":10,"offset":0}` |
| save-assessments | `{"run_id":"...","assessments":[...]}` |
| list-leads | `{"bucket":"Shortlist","new_only":true,"limit":50}` |
| update-lead | `{"lead_id":"...","edits":{"status":"applied","notes":"..."}}` |
| record-application | `{"lead_id":"...","event_id":"stable-id","details":{"type":"application","url":"..."},"edits":{"status":"applied","application_date":"2027-01-06"}}` |
| sync-workbook | `{}` |
| search-plan | `{"config":{"search_strategy":"hybrid","search_phase":"discovery","sort_by":"relevance","date_posted":"past_month","target_companies":["Example"]}}` |
| save-author | `{"author_url":"https://example.com/in/person","employer":"Example","checked_at":"2026-11-10T12:00:00+00:00","checks":{"author_us":{"result":"unknown"},"manager":{"result":"unknown"},"affiliation":{"result":"unknown"}}}` |
| get-author | `{"author_url":"https://example.com/in/person","expected_employer":"Example","max_age_days":30,"contradiction":false}` |
| start-comparison | `{"comparison_id":"pilot-1","arms":{"broad":"hiring scientist ml","intent":"my team hiring machine learning"},"track":"tech","sort_by":"relevance","date_posted":"past_month","budget":{"posts":10,"profiles":3,"jobs":2}}` |
| save-comparison-arm | See bounded audit schema below. |
| comparison-report | `{"comparison_id":"pilot-1"}` |

Ingestion returns post IDs; batch output provides content_digest and resume IDs. Copy them exactly. Optional ingestion fields: `batch_id` (unique within run, identical retries are idempotent) and `loading_actions` (nonnegative integer, default 1). A repeated batch ID with changed input is rejected. Recovered pending posts are available for analysis but do not count as new. Lexically similar posts are flagged, never automatically merged. Fallback captures can acquire a permalink while retaining stable internal IDs.

Editable tracking fields: status, notes, next_action, follow_up_date, application_date, selected_resume. The assessment's resume is immutable evidence; selected_resume records the user's application choice. Statuses: new, reviewing, shortlisted, saved, contacted, applied, interviewing, offer, rejected, withdrawn, dismissed, closed. Event IDs make history idempotent; replay does not revert a later tracking status. Post and assessment versions retain previous evidence when content changes.

`analysis-batch` offsets refer to the current pending list. Obtain all disjoint worker batches before accepting any submissions, or fetch offset zero after a batch completes. Do not increment offsets across a shrinking list. Checkpoint elapsed_seconds is an increment, not a total; do not replay it after a successful response.

Save bulk inputs in ignored .local. Analysis batches include resume variants: coordinator selects relevant excerpts before delegation. Avoid loading the entire database into context.

## Discovery records

### Recommended-feed batches

Start with `{"config":{"collection_source":"for_you","feed_post_count":50}}`. `feed_post_count` counts all distinct inspected outer posts, including skipped posts and sponsored cards. `target_count` applies only to search runs. Search sorting/date filters do not apply to Home For you. Global inspection/load/time/no-progress limits still apply.

```json
{
  "run_id": "...",
  "batch_id": "feed-page-1",
  "loading_actions": 0,
  "elapsed_seconds": 12,
  "items": [
    {"item_key":"123456789", "disposition":"not_hiring", "reason":"Research discussion without a vacancy"},
    {"disposition":"candidate", "reason":"Own-team research opening; needs verification", "post":{
      "url":"https://www.linkedin.com/feed/update/urn:li:activity:987654321/",
      "author_url":"https://www.linkedin.com/in/example-manager/",
      "author_name":"Example Manager",
      "author_position":"Research Manager",
      "content":"Exact expanded source text",
      "posted_date":"2d", "date_precision":"relative", "track":"tech"
    }}
  ]
}
```

Use at most ten items per batch. Dispositions are candidate, not_hiring, out_of_scope and sponsored. A candidate requires a normal Post record; its item_key is derived automatically, or must match that identity if supplied. Skipped items require a stable outer-post ID/permalink or author/content fingerprint, a reason, and no full Post body. Skip keys containing canonical activity/share/ugcPost URLs or URNs normalize to their numeric IDs. Do not use a nested repost's ID. Feed observations are screening records, not scored Excluded leads.

The batch atomically saves screening observations, ingests candidates through normal deduplication, and updates loading/time counters. Exact batch retries return the saved result without changing counters, including after the run stops. Conflicting retries fail. New batches repeat neither inspected keys nor candidates within the run. A fresh daily run counts those cards toward its own inspection budget while preserving global lead history. No-progress means no newly inspected cards after a loading attempt, not no hiring matches.

Returns added post IDs, inspected_count, new_inspected, disposition totals, new_candidates and stop_reason. The feed target produces feed_target_reached; the lower max_inspected cap can stop earlier. Do not charge elapsed_seconds a second time through checkpoint. `feed-audit` returns total and ranked observations with limit 1–100 and nonnegative offset. `run-status` returns inspected_count and disposition totals without full resume text. Workbook Runs includes these counters; candidate rows include discovery_sources. Historic rows without source sightings may have a blank discovery_sources cell.

### Search plans, author evidence and comparisons

`start-run` returns the resolved `search_plan`. Standalone `search-plan` uses only its input and built-in defaults; pass the run's effective config to preserve private settings. `search_phase=discovery` suggests relevance/month only when sort/date are omitted; explicit values always win. An empty employer list marks that lane `requires_scope`; Codex selects a justified scope or skips it explicitly. Global run limits span all lanes.

Author cache checks are exactly author_us, manager and affiliation. Each resolved check needs `{"result":"pass|fail","source_url":"https://...","quote":"exact source excerpt","reason":"why it supports this fact"}`; unknown needs only result. These comparison/cache facts are separate from the assessment Check schema, which uses post-bound evidence IDs. Quotes need semantic review by Codex. A cache record retains history and reports revalidation on age, employer change or contradiction; it never proves own-team hiring for a new post. Pass `author_max_age_days` from the plan as get-author's `max_age_days`.

Comparison protocol and arm submissions are immutable and idempotent. Changed inputs require a new comparison ID. Resume an interrupted comparison by reading comparison-report, which labels missing arms incomplete. Arm order is protocol object order.

```json
{
  "comparison_id": "pilot-1",
  "arm": "broad",
  "observed_filters": "Posts; Top Match; Past month",
  "stop_reason": "sample_cap",
  "profiles_used": ["https://example.com/in/person"],
  "jobs_used": [],
  "observations": [{
    "post_key": "canonical-post-id-or-author-content-fingerprint",
    "rank": 1,
    "author_url": "https://example.com/in/person",
    "source_url": "https://example.com/post/1",
    "excerpt": "Exact screening evidence",
    "promising": true,
    "reason": "Relevant hiring; profile authority unresolved",
    "checks": {"manager": {"result": "unknown"}}
  }]
}
```

Submit each complete arm atomically, preserving all first-N observations and consecutive ranks. Retain partial input files privately while collecting. Allowed checks: active_hiring, relevant_role, author_us, manager, affiliation, own_team, full_time, entry_level, job_us. Omitted checks count as unknown. Profile/JD evidence includes reused cache evidence and failed attempts in usage arrays; each entry charges one check. Do not transfer unused budget between arms. Use a shared post_key across arms for overlap reporting. For rejects without permalinks, preserve the search URL, author and exact excerpt; do not misrepresent the excerpt as complete source content. Fully eligible posts require all checks; resume scoring remains the separate assessment workflow.
