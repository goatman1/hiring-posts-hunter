"""Local planning, dated author evidence and bounded comparison audits. No I/O to services."""
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator


def canonical(url):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.netloc:
        raise ValueError('Evidence and author URLs must be absolute HTTP(S) URLs')
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), '', ''))


def timestamp(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError('Use a timezone-aware ISO timestamp')
    return dt


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Fact(Strict):
    result: Literal['pass', 'fail', 'unknown'] = 'unknown'
    source_url: str = ''
    quote: str = ''
    reason: str = ''

    @model_validator(mode='after')
    def supported(self):
        if self.result != 'unknown':
            canonical(self.source_url)
            if not self.quote.strip() or not self.reason.strip():
                raise ValueError('Resolved checks need a source, exact quote and reasoning')
        return self


class Author(Strict):
    author_url: str
    employer: str = Field(min_length=1)
    checked_at: str
    checks: dict[str, Fact]

    @model_validator(mode='after')
    def verified(self):
        self.author_url = canonical(self.author_url)
        checked = timestamp(self.checked_at)
        if checked > datetime.now(timezone.utc):
            raise ValueError('Author evidence cannot be from the future')
        if set(self.checks) != {'author_us', 'manager', 'affiliation'}:
            raise ValueError('Cache only profile location, management and current affiliation')
        return self


class Budget(Strict):
    posts: int = Field(default=10, ge=1, le=500, strict=True)
    profiles: int = Field(default=3, ge=0, le=100, strict=True)
    jobs: int = Field(default=2, ge=0, le=100, strict=True)


class Protocol(Strict):
    comparison_id: str = Field(min_length=1)
    arms: dict[str, str] = Field(min_length=2, max_length=6)
    track: Literal['tech', 'quant']
    sort_by: Literal['relevance', 'date_posted']
    date_posted: Literal['past_month', 'past_week', 'past_24_hours', 'all_time']
    budget: Budget = Field(default_factory=Budget)
    notes: str = ''


MANAGER_CHECKS = ('active_hiring', 'relevant_role', 'author_us', 'manager', 'affiliation', 'own_team')
ELIGIBILITY_CHECKS = (*MANAGER_CHECKS, 'full_time', 'entry_level', 'job_us')


class Observation(Strict):
    post_key: str = Field(min_length=1)
    rank: int = Field(ge=1, strict=True)
    author_url: str
    source_url: str
    excerpt: str = Field(min_length=1)
    promising: bool
    reason: str = Field(min_length=1)
    checks: dict[str, Fact] = Field(default_factory=dict)

    @model_validator(mode='after')
    def valid(self):
        self.author_url = canonical(self.author_url)
        canonical(self.source_url)
        if set(self.checks) - set(ELIGIBILITY_CHECKS):
            raise ValueError('Unknown comparison check')
        if all(k in self.checks and self.checks[k].result == 'pass' for k in MANAGER_CHECKS) and not self.promising:
            raise ValueError('Verified manager observation must also be promising')
        return self


class Arm(Strict):
    comparison_id: str
    arm: str
    observations: list[Observation]
    profiles_used: list[str] = Field(default_factory=list)
    jobs_used: list[str] = Field(default_factory=list)
    stop_reason: str = Field(min_length=1)
    observed_filters: str = Field(min_length=1)


def immutable(hunter, kind, key, record):
    try:
        old = hunter.get(kind, key)
    except ValueError:
        old = None
    if old is not None and old != record:
        raise ValueError('Conflicting replay; use a new comparison ID for a changed protocol or audit')
    hunter.put(kind, key, record)
    return record


def dispatch(hunter, command, data):
    if command == 'search-plan':
        config = data.get('config', {})
        source = config.get('collection_source', 'search')
        count = config.get('feed_post_count', 50)
        if source not in ('search', 'for_you'):
            raise ValueError('collection_source must be search or for_you')
        if type(count) is not int or not 1 <= count <= 500:
            raise ValueError('feed_post_count must be an integer from 1 to 500')
        if source == 'for_you':
            return {'collection_source': source, 'feed_post_count': count,
                    'feed_url': 'https://www.linkedin.com/feed/foryou/',
                    'order': 'LinkedIn recommendations; verify For you selection',
                    'date_filter': 'No search date filter applied', 'lanes': []}
        strategy = config.get('search_strategy', 'hybrid')
        phase = config.get('search_phase', 'monitoring')
        if strategy not in ('hybrid', 'broad', 'intent', 'employer') or phase not in ('discovery', 'monitoring'):
            raise ValueError('Unsupported search strategy or phase')
        queries = config.get('queries', [
            {'track': 'tech', 'keywords': 'hiring scientist ml'},
            {'track': 'quant', 'keywords': 'hiring quantitative researcher'}])
        intent = config.get('intent_queries', [
            {'track': 'tech', 'keywords': '"my team" hiring "machine learning"'},
            {'track': 'quant', 'keywords': '"my team" hiring "quantitative"'},
            {'track': 'tech', 'keywords': '"join my team" "applied scientist"'},
            {'track': 'quant', 'keywords': '"join my team" "quant"'}])
        for queue in (queries, intent):
            if not isinstance(queue, list) or not queue or any(not isinstance(q, dict) or q.get('track') not in ('tech', 'quant') or not isinstance(q.get('keywords'), str) or not q['keywords'].strip() for q in queue):
                raise ValueError('Queries must be a nonempty list of tech/quant keyword records')
        for name in ('target_companies', 'author_titles'):
            value = config.get(name, [])
            if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
                raise ValueError(f'{name} must be a list of nonempty strings')
        ttl = config.get('author_max_age_days', 30)
        if type(ttl) is not int or ttl <= 0:
            raise ValueError('author_max_age_days must be a positive integer')
        lanes = []
        if strategy in ('hybrid', 'broad'):
            lanes.append({'lane': 'broad', 'queries': queries})
        if strategy in ('hybrid', 'intent'):
            lanes.append({'lane': 'intent', 'queries': intent})
        if strategy in ('hybrid', 'employer'):
            lanes.append({'lane': 'employer', 'queries': queries, 'author_companies': config.get('target_companies', []),
                          'requires_scope': not bool(config.get('target_companies')),
                          'people_location': 'United States', 'author_titles': config.get('author_titles', ['manager', 'director', 'head', 'founder'])})
        sort_by = config.get('sort_by', 'relevance' if phase == 'discovery' else 'date_posted')
        date_posted = config.get('date_posted', 'past_month' if phase == 'discovery' else 'past_week')
        if sort_by not in ('relevance', 'date_posted') or date_posted not in ('past_month', 'past_week', 'past_24_hours', 'all_time'):
            raise ValueError('Unsupported sort/date filter')
        return {'collection_source': source, 'strategy': strategy, 'phase': phase, 'sort_by': sort_by, 'date_posted': date_posted, 'author_max_age_days': ttl, 'lanes': lanes}
    if command == 'save-author':
        record = Author.model_validate(data).model_dump()
        key = record['author_url']
        hunter.put('author-evidence', hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest(), record)
        try:
            previous = hunter.get('author', key)
        except ValueError:
            previous = None
        if previous is None or timestamp(record['checked_at']) >= timestamp(previous['checked_at']):
            hunter.put('author', key, record)
        return record
    if command == 'get-author':
        record = hunter.get('author', canonical(data['author_url']))
        ttl = data.get('max_age_days', 30)
        if type(ttl) is not int or ttl <= 0:
            raise ValueError('max_age_days must be a positive integer')
        age = (datetime.now(timezone.utc) - timestamp(record['checked_at'])).total_seconds() / 86400
        employer_changed = bool(data.get('expected_employer') and data['expected_employer'].casefold().strip() != record['employer'].casefold().strip())
        return {'record': record, 'age_days': age, 'revalidate': age >= ttl or employer_changed or data.get('contradiction', False)}
    if command == 'start-comparison':
        record = Protocol.model_validate(data).model_dump()
        return immutable(hunter, 'comparison', record['comparison_id'], record)
    if command == 'save-comparison-arm':
        record = Arm.model_validate(data).model_dump()
        protocol = hunter.get('comparison', record['comparison_id'])
        if record['arm'] not in protocol['arms']:
            raise ValueError('Arm is absent from the fixed protocol')
        obs = record['observations']
        if len({o['post_key'] for o in obs}) != len(obs) or [o['rank'] for o in obs] != list(range(1, len(obs) + 1)):
            raise ValueError('Use distinct posts in consecutive result order starting at 1')
        for field, used in [('posts', obs), ('profiles', record['profiles_used']), ('jobs', record['jobs_used'])]:
            if len(used) > protocol['budget'][field]:
                raise ValueError(f'{field} budget exceeded')
        profiles = {canonical(u) for u in record['profiles_used']}
        jobs = {canonical(u) for u in record['jobs_used']}
        for o in obs:
            resolved = {k: v for k, v in o['checks'].items() if v['result'] != 'unknown'}
            if any(k in resolved for k in ('author_us', 'manager', 'affiliation')) and o['author_url'] not in profiles:
                raise ValueError('Charge profile evidence (including cached evidence) to the arm')
            for check in resolved.values():
                source = canonical(check['source_url'])
                if source not in {canonical(o['source_url']), o['author_url']} and source not in jobs:
                    raise ValueError('Additional evidence sources must be charged as job checks')
        key = record['comparison_id'] + ':' + record['arm']
        return immutable(hunter, 'comparison-arm', key, record)
    if command == 'comparison-report':
        protocol = hunter.get('comparison', data['comparison_id'])
        results, seen = {}, {}
        for arm in protocol['arms']:
            try:
                audit = hunter.get('comparison-arm', protocol['comparison_id'] + ':' + arm)
            except ValueError:
                results[arm] = {'status': 'incomplete'}
                continue
            obs = audit['observations']
            def passes(o, names):
                return all(o['checks'].get(k, {}).get('result') == 'pass' for k in names)
            verified = [o for o in obs if passes(o, MANAGER_CHECKS)]
            eligible = [o for o in obs if passes(o, ELIGIBILITY_CHECKS)]
            seen[arm] = {o['post_key'] for o in obs}
            results[arm] = dict(status='recorded', inspected=len(obs), promising=sum(o['promising'] for o in obs),
                verified_us_managers=len({o['author_url'] for o in verified}), eligible_posts=len(eligible),
                unresolved_promising=sum(o['promising'] and not passes(o, ELIGIBILITY_CHECKS) and not any(c['result'] == 'fail' for c in o['checks'].values()) for o in obs),
                profiles_used=len(audit['profiles_used']), jobs_used=len(audit['jobs_used']), stop_reason=audit['stop_reason'])
        overlap = {a + ' / ' + b: len(seen[a] & seen[b]) for i, a in enumerate(seen) for b in list(seen)[i + 1:]}
        return {'protocol': protocol, 'arms': results, 'post_overlap': overlap,
                'interpretation': 'Equal action caps; not equal time. Eligibility is not a resume-scored shortlist. Unknown checks do not count as successes.'}
    raise ValueError('Unknown discovery command')


COMMANDS = {'search-plan', 'save-author', 'get-author', 'start-comparison', 'save-comparison-arm', 'comparison-report'}
