# Native browser workflow

Discover browser tools in the current Codex session; use supported inventory/selection APIs and read returned documentation before operating. Prefer semantic locators and observed controls. Do not guess selectors or execute scripts unsupported by the browser tool.

Select the user's existing LinkedIn tab or open LinkedIn in the connected browser. Login/2FA is manual. If logged out, checkpoint stop_reason authentication_required. Resume after login with a new run, retaining the database. Stop on CAPTCHA/rate limits; do not evade challenges.

Search Posts, enter keywords, choose date and sort through visible UI, and verify selected filters. Report unavailable filters instead of silently substituting. Capture direct post permalinks, full expanded text, displayed dates and precision, author name/position/profile URL. Distinguish repost commentary from the original post.

Load more through observed scroll/load-next controls. Ingest each batch once; one ingestion equals one loading action. Checkpoint incremental active seconds, query index, current URL, observed filters, and loading position. Empty ingestions count toward the three-load no-progress limit. Advance queries when exhausted; honor all global stop limits. Count posts, not hyperlinks.

Inspect current personal location, headline, experience, and relevant company/team statements. Employer headquarters do not establish personal location. Save exact excerpts with URLs. Hiring authority requires management evidence AND connection to the advertised team. Confirmed recruiters/agencies/unrelated reposts fail own-team verification. Ambiguity goes to review.

LinkedIn restricts website automation; existing Codex tools do not remove that restriction. Keep runs bounded and obey access controls.
