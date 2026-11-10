# Assessment and worker contract

Assessment fields: post_id, content_digest, role, company, optional requisition_id, checks, scores, resume_id, resume_evidence (exact quotes), explanation, flags, message.

Required checks: active_hiring, full_time, entry_level, author_us, manager, affiliation, own_team. Semantic checks: location, title, skills, start_date, sponsorship. Each check is `{ "result": "pass", "evidence_ids": ["saved ID"], "reason": "explanation" }`. Result is pass/fail/unknown. Pass/fail requires evidence IDs; unknown is appropriate for missing information.

Location/title default to enforce. Skills/start-date/sponsorship default to flag. Any enforced fail excludes; unknown routes to Needs Review. Confirmed recruiters are not own-team managers. Current employer must match hiring company. PhD entry positions qualify even without 'new grad'; explicit senior-only and internships fail.

Scores: role 0–30, skills 0–30, experience 0–25, education 0–15. Award points only for supported alignment and explain gaps. Default threshold 60 is not an interview probability. Select one resume variant and quote it exactly; do not combine conflicting publication/achievement claims. Shortlist drafts require 70–120 words, reference the opportunity, supported qualifications, and a concise request to discuss fit. No invented relationship or attachments.

Workers return assessments or evidence_requests with post IDs. Coordinator alone persists results. Supply requisition_id only for a confirmed company/job identifier, never manufactured from similarity. Submit all roles in one post together. Structural validation does not establish factual truth: coordinator must audit conclusions against excerpts.
