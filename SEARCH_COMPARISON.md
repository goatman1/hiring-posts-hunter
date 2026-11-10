# Search comparison — November 10, 2026

The targeted searches did **not** outperform the broad query in this pilot. Broad discovery should remain part of the workflow.

## Protocol and results

All arms used authenticated LinkedIn Posts, Top Match, Past month, and the first ten distinct posts in result order. The shared budget was **up to 10 posts, 3 profile checks and 2 job-description checks per arm**. These action caps were declared in the chat before collection. This was not an equal-time experiment. Unused verification budget was not transferred or spent on already-rejected posts. Cached evidence was charged to the receiving arm.

| Approach | Query / scope | Inspected | Promising before profile checks | Verified US own-team managers with relevant roles | Fully eligible posts | Profile / JD checks used |
|---|---|---:|---:|---:|---:|---:|
| Broad | `hiring scientist ml` | 10 | 3 | 3 | 1 | 3 / 2 |
| Ownership phrase | `"my team" "hiring" "scientist"` | 10 | 1 | 0 | 0 | 1 / 0 |
| Employer | `hiring scientist ml`, Author company = Amazon | 10 | 2 | 1 | 1 | 2 / 1 |

“Fully eligible” means verified active hiring, relevant work, US author, management responsibility, current affiliation, own-team hiring, full-time employment, US job and junior/PhD-entry suitability. It does not mean resume-scored Shortlist or guaranteed employer acceptance. Two broad-arm promising posts and one phrase-arm post remained unresolved. The second employer-arm prospect was excluded after the profile identified a non-US location.

The employer arm's one eligible post was also in the broad arm: **one distinct eligible opportunity overall**, not two. Other post overlap was zero in this sample. The qualifying JD allowed a PhD as an alternative to a master's plus four years; the years requirement must not be applied to both routes. A different JD required substantial research leadership experience and remained unresolved for early-career suitability.

## What the pilot supports

- Ownership wording reduced obvious recruiter noise but “scientist” without an ML/domain anchor brought wet-lab, senior and overseas roles. One author using “my team” had no verified management responsibility.
- Author company filtering still admitted internal recruiters and overseas teams. It cannot substitute for author-location and role-location checks.
- Keep the broad lane. The implemented intent presets retain a domain anchor, and employer/people targeting can combine current company, US location and leadership hints where the UI supports them. Those refinements need a new comparison; their superiority is **not** established by this pilot.
- Early rejection reduced profile/JD work for plainly unsuitable posts. The sample establishes counts under equal caps, not throughput per minute.

## Evidence and limitations

Collection used Codex's existing connected browser. Sort/date/company controls were visibly checked. Incremental loading supplied more than the initial result batch; only the first ten posts per arm entered the audit. Profiles and two relevant JDs were inspected directly. The eligible post's canonical permalink was resolved and author checked. No messages, connections, applications or uploads were sent.

Private `.local/search-comparison.json` contains the protocol, ranked observations, exact screening/profile/JD excerpts, source URLs, dispositions and usage. `.local/search-comparison-report.json` contains recomputed aggregates. Source excerpts for rejected posts are not represented as full-body captures. The database stores these as comparison audits, separate from resume-scored leads. The fully captured eligible post is also retained as a pending tracking candidate for further resume review.

This is a small, sequential, personalized tech/science pilot, not a randomized trial. Exact scopes were chosen during the session; Amazon was selected after the broad arm and before opening the employer arm, which can introduce selection bias. There was no independent blinded audit. One phrase query and one employer do not represent all intent or employer strategies. Quant, US-filtered People search, author-title targeting, the new domain-anchored intent presets and longitudinal manager monitoring were not tested in this comparison. Relevance/month also differs from the earlier Latest/week smoke test, so changes versus that older test cannot be attributed to query wording alone.
