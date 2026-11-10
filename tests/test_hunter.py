import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.agents/skills/job-search/scripts'))
from job_hunter import Hunter, CHECKS, load_resumes
from openpyxl import load_workbook
import workbook

class HunterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        resumes = self.root / 'resumes'
        resumes.mkdir()
        with ZipFile(resumes / 'tech.docx', 'w') as z:
            z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Python research PhD</w:t></w:r></w:p></w:body></w:document>')
        self.app = Hunter(self.root / 'data')
        self.config = {'resume_dir': str(resumes)}
        self.run = self.app.execute('start-run', {'config': self.config})['run_id']
    def tearDown(self):
        self.app.db.close()
        self.temp.cleanup()
    def ingest(self, n=1, content='We hire researchers'):
        posts = [dict(url=f'https://www.linkedin.com/feed/update/urn:li:activity:{i}/', author_url='https://www.linkedin.com/in/person', author_name='Test Manager', content=content) for i in range(n)]
        return self.app.execute('ingest-posts', {'run_id':self.run, 'posts':posts})
    def assessment(self, pid='0'):
        eid = self.app.execute('save-evidence', {'post_id':pid,'source_url':'https://example.com/profile','quote':'US manager hires own team'})['evidence_id']
        return dict(post_id=pid, content_digest=self.app.get('post',pid)['content_digest'], role='Researcher', company='Example', checks={k:dict(result='pass', evidence_ids=[eid]) for k in (*CHECKS,'location','title')}, scores=dict(role=30,skills=30,experience=20,education=15),resume_id='tech',resume_evidence=['Python research PhD'],explanation='Supported fit',message=' '.join(['word']*80))
    def save(self,a):
        return self.app.execute('save-assessments',{'run_id':self.run,'assessments':[a]})[0]
    def test_duplicates_and_resume(self):
        self.assertEqual(len(self.ingest(30)['added']),30)
        self.assertEqual(self.ingest(30)['added'],[])
        self.app.db.close()
        self.app=Hunter(self.root/'data')
        self.assertEqual(len(self.app.execute('run-status',{'run_id':self.run})['posts']),30)
        self.run=self.app.execute('start-run',{'config':self.config})['run_id']
        self.assertEqual(self.ingest(30)['added'],[])
    def test_bounded_batch(self):
        self.ingest(30)
        self.assertEqual(len(self.app.execute('analysis-batch',{'run_id':self.run})['posts']),10)
        with self.assertRaises(ValueError): self.app.execute('analysis-batch',{'run_id':self.run,'limit':11})
    def test_classification(self):
        self.ingest()
        for key in CHECKS:
            a=self.assessment(); a['checks'][key]['result']='unknown'
            self.assertEqual(self.save(a)['bucket'],'Needs Review')
            a['checks'][key]['result']='fail'
            self.assertEqual(self.save(a)['bucket'],'Excluded')
        a=self.assessment(); a['checks']['sponsorship']=dict(result='fail',evidence_ids=a['checks']['manager']['evidence_ids'])
        self.assertEqual(self.save(a)['bucket'],'Shortlist')
    def test_idempotent_multi_role(self):
        self.ingest(); a=self.assessment(); self.save(a); self.save(a)
        self.assertEqual(len(self.app.all('lead')),1)
        a['role']='ML Engineer'; self.save(a)
        self.assertEqual(len(self.app.all('lead')),2)
    def test_edited_post_stales_assessment(self):
        self.ingest(); a=self.assessment(); result=self.save(a)
        self.ingest(content='New requirements')
        self.assertTrue(self.app.get('lead',result['lead_id'])['stale'])
        with self.assertRaises(ValueError): self.save(a)
    def test_invalid_resume_and_draft(self):
        self.ingest(); a=self.assessment(); a['resume_evidence']=['invented']
        with self.assertRaises(ValueError): self.save(a)
        a=self.assessment(); a['message']='Too short'
        with self.assertRaises(ValueError): self.save(a)
        self.assertEqual(self.app.all('lead'),[])
    def test_repost_grouping(self):
        self.ingest(2)
        for pid in ('0','1'):
            a=self.assessment(pid); a['requisition_id']='R123'; self.save(a)
        self.assertEqual(len(self.app.all('lead')),1)
        self.assertEqual(len(self.app.all('lead')[0]['post_ids']),2)
    def test_history_idempotence(self):
        self.ingest(); key=self.save(self.assessment())['lead_id']
        event={'lead_id':key,'event_id':'event1','details':{'url':'example.com'},'edits':{'status':'applied'}}
        self.app.execute('record-application',event); self.app.execute('record-application',event)
        self.assertEqual(len(self.app.all('event')),1)
        self.assertEqual(self.app.execute('list-leads',{'new_only':True}),[])
    def test_workbook_edits_and_formulas(self):
        self.ingest(content='=HYPERLINK("evil")'); key=self.save(self.assessment())['lead_id']
        path=Path(self.app.execute('sync-workbook',{})['path'])
        book=load_workbook(path); sheet=book['Shortlist']
        self.assertEqual(sheet.cell(2,3).data_type,'s')
        headers=[c.value for c in sheet[1]]
        sheet.cell(2,headers.index('notes')+1,'My note'); book.save(path); book.close()
        self.app.execute('sync-workbook',{})
        self.assertEqual(self.app.get('lead',key)['notes'],'My note')
    def test_locked_export(self):
        original=workbook.os.replace
        def locked(src,dst):
            if Path(dst).name=='leads.xlsx': raise PermissionError('locked')
            return original(src,dst)
        with patch.object(workbook.os,'replace',side_effect=locked):
            result=self.app.execute('sync-workbook',{})
        self.assertTrue(result['locked']); self.assertTrue(Path(result['path']).exists())
    def test_limits(self):
        for _ in range(3): self.app.execute('ingest-posts',{'run_id':self.run,'posts':[]})
        self.assertEqual(self.app.get('run',self.run)['stop_reason'],'no_progress')
    def test_resume_pairing(self):
        path=Path(self.config['resume_dir']); (path/'tech.pdf').write_bytes(b'invalid intentionally')
        self.assertEqual(len(load_resumes(path)),1)
    def test_time_limit(self):
        result=self.app.execute('checkpoint',{'run_id':self.run,'elapsed_seconds':1801})
        self.assertEqual(result['stop_reason'],'time_limit')
    def test_conflicting_workbook_edits(self):
        self.ingest(); key=self.save(self.assessment())['lead_id']
        path=Path(self.app.execute('sync-workbook',{})['path'])
        book=load_workbook(path)
        for name,note in [('Shortlist','first'),('Candidates','second')]:
            sheet=book[name]; headers=[c.value for c in sheet[1]]
            sheet.cell(2,headers.index('notes')+1,note)
        book.save(path); book.close()
        with self.assertRaises(ValueError): self.app.execute('sync-workbook',{})
        self.assertEqual(self.app.get('lead',key)['notes'],'')
    def test_assessment_batch_rollback(self):
        self.ingest(); a=self.assessment(); bad=copy.deepcopy(a); bad['resume_id']='missing'
        with self.assertRaises(ValueError):
            self.app.execute('save-assessments',{'run_id':self.run,'assessments':[a,bad]})
        self.assertEqual(self.app.all('lead'),[])
    def test_url_variants(self):
        self.ingest()
        result=self.app.execute('ingest-posts',{'run_id':self.run,'posts':[dict(url='https://www.linkedin.com/posts/person-post-activity-0-abc?utm_source=test',author_url='https://www.linkedin.com/in/person',author_name='Test Manager',content='We hire researchers')]})
        self.assertEqual(result['added'],[])
        self.assertEqual(len(self.app.all('post')),1)
    def test_edited_post_not_new_candidate(self):
        self.ingest()
        self.run=self.app.execute('start-run',{'config':dict(self.config,target_count=1)})['run_id']
        result=self.ingest(content='Edited')
        self.assertIsNone(result['stop_reason'])
        self.assertEqual(self.app.get('run',self.run)['new_posts'],[])

if __name__=='__main__': unittest.main()
