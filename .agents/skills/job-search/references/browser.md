# Native browser workflow

Discover browser tools in the current Codex session; use supported inventory/selection APIs and read returned documentation before operating. Prefer semantic locators and observed controls. Do not guess selectors or execute scripts unsupported by the browser tool.

Select the user's existing LinkedIn tab or open LinkedIn in the connected browser. Login/2FA is manual. If logged out, checkpoint stop_reason authentication_required. Resume after login with a new run, retaining the database. Stop on CAPTCHA/rate limits; do not evade challenges.

Search Posts, enter keywords, choose date and sort through visible UI, and verify selected filters. Report unavailable filters instead of silently substituting. Capture direct post permalinks, full expanded text, displayed dates and precision, author name/position/profile URL. Distinguish repost commentary from the original post.

Start with short discovery phrases (for example `hiring scientist ml` or `hiring quantitative researcher`). Avoid requiring every desired skill in one query; apply those criteria during evidence review. Broad searches may be dominated by recruiters and senior/non-US roles. Report that outcome without relaxing verification.

Load more through observed scroll/load-next controls. Capture and ingest after each loading action, with a unique `batch_id` and the actual `loading_actions` count (zero for the initial page; default one for compatibility). Retrying the same batch ID and identical payload returns the original result without increasing counters. Checkpoint incremental active seconds, query index, current URL, observed filters, and loading position. Empty ingestions count toward the three-batch no-progress limit; send them only after a loading attempt. Advance queries when exhausted; honor all global stop limits. Count posts, not hyperlinks.

If Copy link reports success but the browser clipboard is empty, inspect the notification's View post link when available. Wait for that link to change, follow the observed short link in a detail tab, and verify the author/content before recording the resolved URL. Notifications can momentarily retain the previous post's link. Never treat a tracking redirect or a nested repost's link as the outer post's identity. Preserve the displayed relative date: a repost's date can differ from the original source. Store explanatory evidence when dates disagree.

Inspect current personal location, headline, experience, and relevant company/team statements. Employer headquarters do not establish personal location. Save exact excerpts with URLs. Hiring authority requires management evidence AND connection to the advertised team. Confirmed recruiters/agencies/unrelated reposts fail own-team verification. Ambiguity goes to review.

LinkedIn restricts website automation; existing Codex tools do not remove that restriction. Keep runs bounded and obey access controls.
