"""Local-only persistence interface. Browser and model operations belong to Codex."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, unquote
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

CHECKS = ('active_hiring', 'full_time', 'entry_level', 'author_us', 'manager', 'affiliation', 'own_team')
STATUSES = {'new', 'reviewing', 'shortlisted', 'saved', 'contacted', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn', 'dismissed', 'closed'}
HISTORY = {'contacted', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn', 'dismissed', 'closed'}

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def canonical(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), '', ''))

def similar_content(left, right):
    # Bounded linear-time lexical hint, never evidence that two roles are the same.
    def shingles(text):
        words = text.casefold().split()
        return set(zip(words, words[1:], words[2:]))
    if left == right:
        return True
    a, b = shingles(left), shingles(right)
    return bool(a and b) and len(a & b) / len(a | b) >= 0.85

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Post(Strict):
    url: str = ''
    author_url: str
    author_name: str
    author_position: str = ''
    content: str = Field(min_length=1)
    posted_date: str = ''
    date_precision: str = 'unknown'
    track: str = 'tech'

class Check(Strict):
    result: str
    evidence_ids: list[str] = []
    reason: str = ''

    @model_validator(mode='after')
    def validate_check(self):
        if self.result not in {'pass', 'fail', 'unknown'}:
            raise ValueError('result must be pass, fail, or unknown')
        if self.result != 'unknown' and not self.evidence_ids:
            raise ValueError('pass/fail requires evidence_ids')
        return self

class Scores(Strict):
    role: int = Field(ge=0, le=30)
    skills: int = Field(ge=0, le=30)
    experience: int = Field(ge=0, le=25)
    education: int = Field(ge=0, le=15)

class Assessment(Strict):
    post_id: str
    content_digest: str
    role: str = Field(min_length=1)
    company: str = Field(min_length=1)
    requisition_id: str = ''
    checks: dict[str, Check]
    scores: Scores
    resume_id: str
    resume_evidence: list[str] = Field(min_length=1)
    explanation: str = Field(min_length=1)
    flags: list[str] = []
    message: str = ''

    @model_validator(mode='after')
    def validate_checks(self):
        if not set(CHECKS).issubset(self.checks):
            raise ValueError('missing core verification checks')
        return self

def load_resumes(directory):
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    from pypdf import PdfReader
    paths = {}
    for path in sorted(Path(directory).glob('*')):
        if path.suffix.lower() in {'.docx', '.pdf'}:
            if path.stem not in paths or path.suffix.lower() == '.docx':
                paths[path.stem] = path
    output = []
    for stem, path in paths.items():
        if path.suffix.lower() == '.docx':
            with ZipFile(path) as archive:
                root = ET.fromstring(archive.read('word/document.xml'))
            text = '\n'.join(''.join(p.itertext()) for p in root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
        else:
            text = '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
        output.append(dict(id=stem, path=str(path.resolve()), digest=digest(text), text=text))
    if not output:
        raise ValueError('No readable resume variants found')
    return output

class Hunter:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.directory / 'jobs.sqlite3')
        self.db.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, data TEXT, PRIMARY KEY(kind,id))')
        self.db.commit()

    def get(self, kind, key):
        row = self.db.execute('SELECT data FROM records WHERE kind=? AND id=?', (kind, key)).fetchone()
        if row is None:
            raise ValueError(f'Unknown {kind}: {key}')
        return json.loads(row[0])

    def all(self, kind):
        return [json.loads(r[0]) for r in self.db.execute('SELECT data FROM records WHERE kind=? ORDER BY id', (kind,))]

    def put(self, kind, key, data):
        self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)', (kind, key, json.dumps(data, ensure_ascii=False)))

    def execute(self, command, data):
        with self.db:
            return self.dispatch(command, data)

    def dispatch(self, command, data):
        from discovery import COMMANDS, dispatch
        if command in COMMANDS:
            return dispatch(self, command, data)
        if command == 'init':
            return {'data_dir': str(self.directory), 'schema_version': 1}
        if command == 'start-run':
            config = json.loads((Path(__file__).resolve().parents[4] / 'config.example.json').read_text())
            local_config = Path(__file__).resolve().parents[4] / 'config.local.json'
            if local_config.exists():
                config.update(json.loads(local_config.read_text(encoding='utf-8-sig')))
            overrides = data.get('config', {})
            config['filters'] = {**config['filters'], **overrides.get('filters', {})}
            config.update({k: v for k, v in overrides.items() if k != 'filters'})
            if not 0 <= config['shortlist_threshold'] <= 100:
                raise ValueError('shortlist_threshold must be 0..100')
            if set(config['filters']) - {'location', 'title', 'skills', 'start_date', 'sponsorship'}:
                raise ValueError('Unknown semantic filter')
            if config['sort_by'] not in {'date_posted', 'relevance'} or config['date_posted'] not in {'past_week', 'past_month', 'past_24_hours', 'all_time'}:
                raise ValueError('Unsupported sort/date filter')
            for field in ('target_count', 'max_inspected', 'max_loading_actions', 'max_minutes', 'no_progress_limit'):
                if not isinstance(config[field], int) or config[field] <= 0:
                    raise ValueError(f'{field} must be a positive integer')
            if any(v not in {'off', 'flag', 'enforce'} for v in config['filters'].values()):
                raise ValueError('Invalid semantic filter mode')
            plan = dispatch(self, 'search-plan', {'config': config})
            run = dict(id=uuid.uuid4().hex, config=config, started=now(), posts=[], new_posts=[], inspected=[], loads=0, stalled=0, elapsed_seconds=0, stop_reason=None, progress={}, resumes=load_resumes(config['resume_dir']))
            self.put('run', run['id'], run)
            return {'run_id': run['id'], 'config': config, 'search_plan': plan}
        if command in {'run-status', 'checkpoint', 'ingest-posts', 'analysis-batch', 'save-assessments'}:
            run = self.get('run', data['run_id'])
        if command == 'run-status':
            return {k: v for k, v in run.items() if k not in {'resumes', 'inspected'}}
        if command == 'checkpoint':
            run['elapsed_seconds'] += max(0, float(data.get('elapsed_seconds', 0)))
            run['progress'].update(data.get('progress', {}))
            if data.get('stop_reason'):
                run['stop_reason'] = data['stop_reason']
            self.stop(run)
            self.put('run', run['id'], run)
            return {'stop_reason': run['stop_reason']}
        if command == 'ingest-posts':
            batch_key = digest(run['id'] + '|' + data['batch_id']) if data.get('batch_id') else None
            request_digest = digest(json.dumps(data, sort_keys=True))
            if batch_key:
                previous = next((b for b in self.all('ingestion') if b['id'] == batch_key), None)
                if previous:
                    if previous['request_digest'] != request_digest:
                        raise ValueError('Conflicting repeated ingestion batch_id')
                    return previous['result']
            if run['stop_reason']:
                return {'added': [], 'stop_reason': run['stop_reason']}
            posts = [Post.model_validate(p).model_dump() for p in data['posts']]
            loading_actions = data.get('loading_actions', 1)
            if type(loading_actions) is not int or loading_actions < 0:
                raise ValueError('loading_actions must be a nonnegative integer')
            added = []
            for post in posts:
                match = re.search(r'(?:activity|ugcPost|share)[:\-](\d+)', unquote(post['url']))
                key = match.group(1) if match else digest(canonical(post['url']) if post['url'] else canonical(post['author_url']) + ' ' + ' '.join(post['content'].split()))
                fingerprint = digest(canonical(post['author_url']) + ' ' + ' '.join(post['content'].split()))
                prior_posts = self.all('post')
                # Promote an exact fallback capture without changing IDs referenced by evidence/history.
                alias = next((x for x in self.all('post-alias') if x['id'] == key), None)
                if alias:
                    key = alias['post_id']
                else:
                    fallback = [p for p in prior_posts if p.get('fingerprint') == fingerprint and (not p['url'] or not post['url'])]
                    if len(fallback) == 1:
                        self.put('post-alias', key, {'id': key, 'post_id': fallback[0]['id']})
                        key = fallback[0]['id']
                try:
                    old = self.get('post', key)
                except ValueError:
                    old = None
                if old and not post['url']:
                    post['url'] = old['url']
                similarities = [p['id'] for p in prior_posts if p['id'] != key and similar_content(p['content'], post['content'])]
                post.update(id=key, content_digest=digest(post['content']), first_seen=old['first_seen'] if old else now(), last_seen=now())
                post.update(fingerprint=fingerprint, similar_post_ids=similarities)
                if old and old['content_digest'] != post['content_digest']:
                    self.put('post-version', digest(key + old['content_digest']), old)
                self.put('post', key, post)
                if key not in run['inspected']:
                    run['inspected'].append(key)
                if old is None:
                    run['posts'].append(key)
                    run['new_posts'].append(key)
                    added.append(key)
                elif old['content_digest'] != post['content_digest']:
                    for lead in self.all('lead'):
                        if key in lead['post_ids']:
                            lead['bucket'] = 'Needs Review'
                            lead['stale'] = True
                            self.put('lead', lead['id'], lead)
                    if key not in run['posts']:
                        run['posts'].append(key)
                elif key not in run['posts']:
                    completed = any(a['post_id'] == key and a['content_digest'] == post['content_digest'] for a in self.all('assessment'))
                    if not completed:
                        run['posts'].append(key)
                if len(run['new_posts']) >= run['config']['target_count'] or len(run['inspected']) >= run['config']['max_inspected']:
                    break
            run['loads'] += loading_actions
            run['stalled'] = 0 if added else run['stalled'] + 1
            self.stop(run)
            self.put('run', run['id'], run)
            result = {'added': added, 'stop_reason': run['stop_reason']}
            if batch_key:
                self.put('ingestion', batch_key, {'id': batch_key, 'request_digest': request_digest, 'result': result})
            return result
        if command == 'save-evidence':
            post = self.get('post', data['post_id'])
            if not data.get('quote') or not data.get('source_url'):
                raise ValueError('Evidence requires source_url and quote')
            key = digest(data['post_id'] + post['content_digest'] + data['source_url'] + data['quote'])
            self.put('evidence', key, dict(data, id=key, captured_at=now(), content_digest=post['content_digest']))
            return {'evidence_id': key}
        if command == 'analysis-batch':
            size = data.get('limit', 10)
            if type(size) is not int or not 1 <= size <= 10:
                raise ValueError('Batch limit must be 1..10')
            if type(data.get('offset', 0)) is not int or data.get('offset', 0) < 0:
                raise ValueError('offset must be a nonnegative integer')
            completed = {a['post_id']: a['content_digest'] for a in self.all('assessment')}
            posts = [self.get('post', k) for k in run['posts']]
            posts = [p for p in posts if completed.get(p['id']) != p['content_digest']][data.get('offset', 0):][:size]
            return {'posts': posts, 'evidence': [e for e in self.all('evidence') if e['post_id'] in {p['id'] for p in posts}], 'resumes': run['resumes']}
        if command == 'save-assessments':
            result = []
            for raw in data['assessments']:
                a = Assessment.model_validate(raw).model_dump()
                post = self.get('post', a['post_id'])
                if a['post_id'] not in run['posts'] or post['content_digest'] != a['content_digest']:
                    raise ValueError('Assessment is stale or outside this run')
                resume = next((r for r in run['resumes'] if r['id'] == a['resume_id']), None)
                if resume is None or any(q not in resume['text'] for q in a['resume_evidence']):
                    raise ValueError('Resume evidence must quote selected variant exactly')
                for check in a['checks'].values():
                    for eid in check['evidence_ids']:
                        evidence = self.get('evidence', eid)
                        if evidence['post_id'] != a['post_id']:
                            raise ValueError('Evidence belongs to another post')
                        if evidence['content_digest'] != a['content_digest']:
                            raise ValueError('Evidence predates the edited post; verify and save it again')
                checks = [a['checks'][k] for k in CHECKS]
                for k, mode in run['config']['filters'].items():
                    if mode == 'enforce':
                        checks.append(a['checks'].get(k, {'result': 'unknown'}))
                    elif mode == 'flag':
                        check = a['checks'].get(k, {'result': 'unknown', 'reason': 'Not specified'})
                        if check['result'] != 'pass':
                            flag = f"{k}: {check['result']} — {check.get('reason', '')}"
                            if flag not in a['flags']:
                                a['flags'].append(flag)
                score = sum(a['scores'].values())
                bucket = 'Excluded' if any(c['result'] == 'fail' for c in checks) else 'Needs Review' if any(c['result'] == 'unknown' for c in checks) else 'Shortlist' if score >= run['config']['shortlist_threshold'] else 'Candidates'
                if bucket == 'Shortlist' and not 70 <= len(a['message'].split()) <= 120:
                    raise ValueError('Shortlist draft must contain 70..120 words')
                key = digest(a['company'].casefold().strip() + '|' + a['requisition_id']) if a['requisition_id'] else digest(a['post_id'] + '|' + a['role'].casefold().strip())
                try:
                    lead = self.get('lead', key)
                except ValueError:
                    lead = dict(id=key, post_ids=[], status='new', notes='', next_action='', follow_up_date='', application_date='')
                lead.update(assessment=a, bucket=bucket, match_score=score, stale=False)
                lead.setdefault('selected_resume', a['resume_id'])
                if a['post_id'] not in lead['post_ids']:
                    lead['post_ids'].append(a['post_id'])
                self.put('lead', key, lead)
                self.put('assessment', digest(a['post_id'] + '|' + a['role'].casefold().strip()), a)
                self.put('assessment-version', digest(json.dumps(a, sort_keys=True)), a)
                result.append({'lead_id': key, 'bucket': bucket})
            return result
        if command == 'list-leads':
            leads = self.all('lead')
            return [l for l in leads if (not data.get('bucket') or l['bucket'] == data['bucket']) and (not data.get('new_only') or l['status'] not in HISTORY)][:min(data.get('limit', 50), 100)]
        if command in {'update-lead', 'record-application'}:
            lead = self.get('lead', data['lead_id'])
            edits = data.get('edits', {})
            if set(edits) - {'status', 'notes', 'next_action', 'follow_up_date', 'application_date', 'selected_resume'}:
                raise ValueError('Unsupported tracking edit')
            if 'status' in edits and edits['status'] not in STATUSES:
                raise ValueError('Invalid status')
            lead.update(edits)
            if command == 'record-application':
                event = dict(id=data['event_id'], lead_id=lead['id'], recorded_at=now(), details=data['details'])
                try:
                    previous = self.get('event', event['id'])
                except ValueError:
                    previous = None
                if previous and (previous['lead_id'] != event['lead_id'] or previous['details'] != event['details']):
                    raise ValueError('Conflicting repeated event ID')
                if previous:
                    return self.get('lead', data['lead_id'])
                self.put('event', event['id'], previous or event)
            self.put('lead', lead['id'], lead)
            return lead
        if command == 'sync-workbook':
            from workbook import sync
            return sync(self)
        raise ValueError('Unknown command')

    def stop(self, run):
        c = run['config']
        for condition, reason in ((len(run['new_posts']) >= c['target_count'], 'target_reached'), (len(run['inspected']) >= c['max_inspected'], 'inspection_limit'), (run['loads'] >= c['max_loading_actions'], 'loading_limit'), (run['stalled'] >= c['no_progress_limit'], 'no_progress'), (run['elapsed_seconds'] >= c['max_minutes'] * 60, 'time_limit')):
            if condition and not run['stop_reason']:
                run['stop_reason'] = reason

def main():
    # Windows redirected stdout may otherwise reject Unicode in post/resume JSON.
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--data-dir', type=Path, default=Path('.local'))
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding='utf-8-sig')) if args.input else {}
        app = Hunter(args.data_dir)
        try:
            print(json.dumps(app.execute(args.command, data), ensure_ascii=False))
        finally:
            app.db.close()
    except Exception as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
