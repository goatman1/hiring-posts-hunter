# Discovery strategy and comparisons

Read this before collecting posts. Use `search-plan` to resolve the editable strategy configuration. Helpers return a plan; Codex operates the connected browser.

## Search lanes

Use a hybrid of three lanes, alternating tech and quant within each lane:

- **Broad**: retain short domain queries such as `hiring scientist ml` and `hiring quantitative researcher`. These preserve recall when managers do not use a particular phrase.
- **Intent**: combine one ownership phrase with a domain anchor, e.g. `"my team" hiring "machine learning"`, `"join my team" "applied scientist"`, or `"my team" hiring "quantitative"`. Rotate short queries instead of constructing a large Boolean expression. Scientist alone attracts wet-lab research. Never require "new grad" or exclude every occurrence of "senior": a senior manager may be hiring juniors, and multi-role posts need separate decisions.
- **Employer/people**: use configured target employers. In Posts, distinguish **Author company** (employees) from **From company** (company-page posts). Where available, Author Keywords / Title can prioritize manager, director, head, or founder; title is only a discovery hint. Alternatively use People search with US location, current company and a relevant leadership title, then inspect recent posts or use From member. Actively hiring is optional and may require Premium. Record unavailable filters and the fallback used. A US company filter does not establish the author's or job's location.

For initial discovery, explicitly select relevance / past month. For monitoring, use latest / past week. Existing explicit sort/date overrides win. Do not silently change filters partway through a measured arm. Confirm the selected UI state after applying filters.

## Cheap screening before profile visits

Read the post and linked role card first. Record the exact rejection reason for explicit third-party recruiting, closed hiring, commentary, overseas-only jobs, senior-only roles, internships-only posts or unrelated disciplines. Split multi-role posts: a senior opening does not eliminate a second eligible opening. Fixed-term does not by itself prove part-time; preserve uncertainty about employment type. PhD-entry eligibility can differ from the master's experience requirement.

Prioritize remaining posts with explicit own-team hiring, relevant work and a US job signal. Check author location, current affiliation and actual team leadership on the profile. "My team" can be written by an individual contributor; a manager title alone proves neither ownership nor hiring authority. Then inspect the linked JD for full-time, US location and early-career eligibility, and only then spend context on resume scoring and outreach. Missing evidence goes to Needs Review, not a fabricated pass or automatic exclusion.

Use `save-author` / `get-author` to reuse dated profile evidence. The default freshness window is 30 days; changed employer, contradictory content or a stale record requires revalidation. Cached profile facts never verify a new post's active hiring or own-team claim. Attach the relevant quotes to each post using save-evidence before assessment.

For routine runs, inspect an initial ten posts per query, checkpoint inspected / promising / verified / eligible counts, then shift effort toward productive queries while retaining a broad exploration lane. Report unique authors as well as unique posts. Do not optimize on reactions, raw hits, or unresolved candidates. Global collection limits still apply across all lanes.

## Equal-budget pilot

Before browsing, save a `start-comparison` protocol: exact queries/scopes, arm order, shared track/sort/date, maximum unique inspected posts, profile checks and JD checks per arm. Choose employers before inspecting that arm. Suggested small pilot: 10 posts, 3 author checks, 2 JD checks per arm. These are equal **caps**, not equal elapsed time or guaranteed equal expenditure. Count cached profile/JD evidence against the same cap when it is used. If measuring time, predeclare active collection/verification timing and exclude coding interruptions consistently.

Inspect the first N unique posts in result order, without substituting attractive later posts. Select verification targets using the same early-screen rules. Preserve rank, source URL, excerpts, rejection reasons and unknowns. A repeated post counts once within an arm and once in each arm where found; never let database global dedup penalize later arms. Do not add discoveries from profile activity to the arm sample. Charge all profile/JD checks, including failed attempts. Stop at caps, exhaustion, three stalled loads or authentication/rate-limit challenges. Record shortfalls.

Use `save-comparison-arm` to submit the bounded audit, then `comparison-report`. Reports distinguish promising posts, distinct verified US own-team managers with relevant roles, and posts with fully verified US full-time early-career openings. The last category is eligibility, **not** a resume-scored Shortlist. Unknown is never a success. Store source excerpts privately; publish only aggregate results. Keep negative results. A personalized, sequential, ten-post pilot cannot establish general superiority; report overlap, unused budget, scope limitations and any protocol changes. Future query refinements are exploratory until tested in a new fixed protocol.
