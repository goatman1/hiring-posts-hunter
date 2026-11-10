import json
import os
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

EDITABLE = ('status', 'notes', 'next_action', 'follow_up_date', 'application_date')
COLUMNS = ('role', 'posted date', 'original content', 'poster name', 'poster position', 'match score', 'reach out message', 'lead_id', 'company', 'track', 'post_url', 'profile_url', 'verification', 'resume', 'eligibility flags', *EDITABLE)

def write_row(sheet, values):
    sheet.append([str(v) if v is not None else '' for v in values])
    for cell in sheet[sheet.max_row]:
        cell.data_type = 's'
        cell.alignment = Alignment(vertical='top', wrap_text=True)

def sync(app):
    path = app.directory / 'leads.xlsx'
    baseline_path = app.directory / 'workbook-baseline.json'
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    edits = {}
    if path.exists() and baseline:
        book = load_workbook(path)
        try:
            for sheet in book:
                rows = sheet.iter_rows(values_only=True)
                headers = next(rows, ())
                if 'lead_id' not in headers or 'status' not in headers:
                    continue
                for row in rows:
                    item = dict(zip(headers, row))
                    key = item['lead_id']
                    if key not in baseline:
                        continue
                    for field in EDITABLE:
                        value = str(item.get(field) or '')
                        old = baseline[key].get(field, '')
                        if value != old:
                            pair = (key, field)
                            if pair in edits and edits[pair] != value:
                                raise ValueError(f'Conflicting workbook edits: {key} {field}')
                            current = app.get('lead', key).get(field, '')
                            if current != old and current != value:
                                raise ValueError(f'Workbook/database conflict: {key} {field}')
                            edits[pair] = value
        finally:
            book.close()
    for (key, field), value in edits.items():
        app.dispatch('update-lead', {'lead_id': key, 'edits': {field: value}})
    book = Workbook()
    book.remove(book.active)
    sheets = {name: book.create_sheet(name) for name in ('Shortlist', 'Needs Review', 'Candidates', 'Excluded', 'Applications', 'Runs')}
    for name in ('Shortlist', 'Needs Review', 'Candidates', 'Excluded'):
        write_row(sheets[name], COLUMNS)
    from job_hunter import HISTORY
    baseline = {}
    for lead in app.all('lead'):
        a = lead['assessment']
        post = app.get('post', a['post_id'])
        content = post['content']
        if len(content) > 32000:
            source = app.directory / ('post-' + post['id'] + '.txt')
            source.write_text(content, encoding='utf-8')
            content = content[:31000] + '\nFull content: ' + str(source)
        values = (a['role'], post['posted_date'], content, post['author_name'], post['author_position'], lead['match_score'], a['message'], lead['id'], a['company'], post['track'], post['url'], post['author_url'], json.dumps(a['checks']), a['resume_id'], '; '.join(a['flags']), *(lead.get(k, '') for k in EDITABLE))
        write_row(sheets['Candidates'], values)
        if lead['bucket'] != 'Candidates' and not (lead['bucket'] == 'Shortlist' and lead['status'] in HISTORY):
            write_row(sheets[lead['bucket']], values)
        baseline[lead['id']] = {k: lead.get(k, '') for k in EDITABLE}
    assessed = {p for l in app.all('lead') for p in l['post_ids']}
    for post in app.all('post'):
        if post['id'] not in assessed:
            write_row(sheets['Candidates'], ('Pending analysis', post['posted_date'], post['content'][:32000], post['author_name'], post['author_position'], '', '', '', '', post['track'], post['url'], post['author_url']))
    write_row(sheets['Applications'], ('event_id', 'lead_id', 'recorded_at', 'details'))
    for event in app.all('event'):
        write_row(sheets['Applications'], (event['id'], event['lead_id'], event['recorded_at'], json.dumps(event['details'])))
    write_row(sheets['Runs'], ('run_id', 'started', 'posts', 'loads', 'elapsed_seconds', 'stop_reason', 'progress'))
    for run in app.all('run'):
        write_row(sheets['Runs'], (run['id'], run['started'], len(run['posts']), run['loads'], run['elapsed_seconds'], run['stop_reason'], json.dumps(run['progress'])))
    for sheet in book:
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='17365D')
            sheet.column_dimensions[cell.column_letter].width = 26
        sheet.column_dimensions['C'].width = 65
        sheet.column_dimensions['G'].width = 65
    temporary = app.directory / 'leads.pending.xlsx'
    book.save(temporary)
    book.close()
    try:
        os.replace(temporary, path)
    except PermissionError:
        path = app.directory / ('leads-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.xlsx')
        os.replace(temporary, path)
        return {'path': str(path), 'locked': True, 'imported_edits': len(edits)}
    temporary = baseline_path.with_suffix('.pending')
    temporary.write_text(json.dumps(baseline), encoding='utf-8')
    os.replace(temporary, baseline_path)
    return {'path': str(path), 'locked': False, 'imported_edits': len(edits)}
