# Validation

Tested with the existing Codex Python 3.12.14 runtime and Pydantic, openpyxl, pypdf. Helpers contain no browser, network, model, or agent-framework dependency. Run `python -m unittest discover -s tests -v` from this repository.

## Automated checks

The For you update passes 44 tests total: the previous 35 plus 9 feed tests. Coverage includes all-card inspection counts independent of new-candidate targets, input/batch bounds, transactional rollback, replay-safe time/load counters, stalled loading versus new non-hiring cards, cross-source and repeat-day deduplication, fallback-permalink promotion, interrupted-run recovery, preservation of applied status on edits, and workbook source/counter columns.

## For you smoke test — November 10, 2026

The existing authenticated LinkedIn tab visibly had For you selected and Sort by Top. Two Load more actions supplied a bounded sample of ten actual outer post cards. A people-recommendation widget labeled Feed post was excluded from the count. The sample contained six non-hiring posts, three sponsored cards and one student-internship-only opening, yielding zero candidates for the configured full-time junior/PhD-entry scope. Recommendations were not treated as evidence of managerial hiring.

The new ingest-feed command persisted ten minimal screening records, stopped with feed_target_reached, and returned the identical result on batch replay without increasing counters. Workbook synchronization succeeded. Private request/report files are in .local/feed-smoke-request.json and .local/feed-smoke-report.json. Rejected-post fallback fingerprints used observed outer authors and distinctive text excerpts; one direct outer post ID was available. Unrelated full bodies were not persisted. Active collection seconds were not instrumented for this manual smoke test; time-limit behavior is covered synthetically.

This tests source selection, incremental loading, bounded screening, persistence and replay. It does not establish feed precision, live positive-candidate capture/assessment, or unattended browser availability. Candidate ingestion, shared history, edits and source provenance are covered by synthetic tests. Scheduling was explicitly deferred by the user: no automation was created or activated. The feed reference contains a reusable prompt for later scheduling through Codex.

## Earlier validation

The strategy update passes 35 tests total: the 27 baseline tests below plus 8 tests for search mode/scope resolution, author evidence freshness/history, employer-change revalidation, fixed comparison protocols, interrupted comparisons, action caps, cached-evidence charging, replay conflicts, per-arm overlap and distinct-author counting. Unknown author location, management, affiliation or team ownership cannot count as a verified manager. [The equal-cap live comparison](SEARCH_COMPARISON.md) records the three-arm tech pilot and its limitations.

The search-plan CLI and live comparison persistence/replay were exercised. The eligible source was added to the existing tracker and the workbook synchronized successfully without duplicate ingestion. The skill-creator quick validator could not run because its separate PyYAML dependency is absent; frontmatter and relative reference targets were checked directly. No dependency was added for that optional validator.

27 synthetic tests cover duplicate ingestion, URL variants including `ugcPost-` and URNs, fallback-ID promotion, edited posts and retained versions, confirmed requisition grouping, separate roles, pending-post recovery, bounded batches, repeated assessments and transaction rollback, verification routing, draft/provenance validation, DOCX/PDF pairing, application-event replay, spreadsheet tracking edits/conflicts, text/formula safety, long pending-post content, locked-export fallback, collection limits, uncertain similarity flags, and UTF-8 CLI output under Windows legacy encoding.

Classification tests establish routing behavior, not independent semantic judgment. Helper evidence IDs and exact resume quotes cannot prove that a source supports a conclusion. Codex must review those conclusions. Locked exports are simulated with a PermissionError; no live Excel lock was exercised.

## Live smoke test - November 10, 2026

An earlier attempt stopped on a reCAPTCHA service error. A subsequent run succeeded through the existing connected in-app browser with normal authenticated LinkedIn access. No additional browser installation or model API was used.

- Query: `hiring scientist ml`; Posts, Latest, Past week visibly selected.
- Incremental loading grew the observed result count from 9 to 15, 21, 27, and 33. The first 30 candidates were retained; these are search candidates, not 30 qualified managers.
- All 30 source links were resolved in the browser and checked against the expected author. Empty clipboard reads were recovered using the notification's View post link; one stale notification link was detected and corrected.
- Full rendered body text was captured for 30 posts. Expansion checks did not change the captured bodies. Local content checksums matched all 30 browser captures. Relative dates are retained as displayed, without invented exact timestamps; repost/source dates can differ.
- Local ingestion stored 30 unique posts. Re-ingestion in another run added zero posts. Repeated assessment submission was exercised against saved live data; ten-post batch bounds are covered by automated tests.
- Ten posts were reviewed, yielding 19 distinct role/disposition records: 13 Excluded, 6 Needs Review, 0 Shortlist. The remaining 20 posts are pending analysis. Multi-role posts stayed separate.
- The audit covered non-vacancy commentary, staffing-vendor solicitation, contract/senior roles, non-US job locations, explicit third-party affiliation disclaimers, new-grad/full-time claims, and unresolved hiring authority. Three manager profiles were checked for personal US location, current employer, and management evidence; own-team hiring was checked against their posts.
- Start-date and citizenship/sponsorship concerns remained flags. Unknown employment type, seniority, job location, and author authority remained unresolved, even where the resume-fit score exceeded 60. Review drafts were saved locally; no messages, connections, uploads, or applications were sent.
- SQLite, source JSON, evidence, audit records, resume extracts, and the six-tab workbook remain in ignored local storage. No live candidate or resume data is committed.

This completes the 30-candidate collection, repeated-ingestion check, and ten-post assessment audit. It does not establish quant-search coverage, calibrated scoring accuracy, employer-side vacancy availability, all 30 posts' suitability, or parallel-worker execution. Those were not tested live. No result is presented as a verified shortlisted opportunity.

Live findings fixed in this revision: missing `ugcPost-` identity recognition, pending-post recovery across runs, fallback identity promotion, ingestion retry counters, replay reverting application status, prior evidence/source version retention, pending workbook IDs/full-content references, expensive similarity comparisons, and Windows Unicode JSON output.
