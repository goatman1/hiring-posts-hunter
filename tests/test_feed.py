import copy
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.agents/skills/job-search/scripts'))
from job_hunter import Hunter, CHECKS


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        resumes = self.root / 'resumes'
        resumes.mkdir()
        with ZipFile(resumes / 'tech.docx', 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Python research PhD</w:t></w:r></w:p></w:body></w:document>')
        self.app = Hunter(self.root / 'data')
        self.config = dict(resume_dir=str(resumes), collection_source='for_you', feed_post_count=10)
        self.run = self.start()

    def tearDown(self):
        self.app.db.close()
        self.temp.cleanup()

    def start(self, **overrides):
        return self.app.execute('start-run', {'config':{**self.config, **overrides}})['run_id']

    def candidate(self, key='10', content='My team hires ML researchers'):
        return dict(disposition='candidate', reason='Relevant explicit team hiring; verify authority',
                    post=dict(url=f'https://www.linkedin.com/feed/update/urn:li:activity:{key}/',
                              author_url='https://www.linkedin.com/in/test', author_name='Test', content=content))

    def skip(self, key, disposition='not_hiring'):
        return dict(item_key=key, disposition=disposition, reason='Synthetic screening decision')

    def batch(self, items, batch_id='first', **extra):
        return self.app.execute('ingest-feed', dict(run_id=self.run, batch_id=batch_id, items=items, **extra))

    def test_total_inspected_is_not_candidate_target(self):
        self.run=self.start(feed_post_count=3, target_count=1)
        result=self.batch([self.candidate(), self.skip('skip'), self.candidate('11'), self.candidate('12')])
        self.assertEqual(result['inspected_count'],3)
        self.assertEqual(result['new_candidates'],2)
        self.assertEqual(result['stop_reason'],'feed_target_reached')
        self.assertEqual(len(self.app.all('post')),2)
        self.assertEqual(len(self.app.all('feed-observation')),3)
        audit=self.app.execute('feed-audit',{'run_id':self.run,'limit':1,'offset':1})
        self.assertEqual(audit['total'],3)
        self.assertEqual(audit['observations'][0]['rank'],2)
        with self.assertRaises(ValueError): self.app.execute('feed-audit',{'run_id':self.run,'limit':101})

    def test_duplicate_ids_replay_and_no_progress(self):
        first=[self.skip('urn:li:activity:1'), self.skip('1'), self.skip('ad','sponsored')]
        result=self.batch(first,loading_actions=1,elapsed_seconds=4)
        self.assertEqual(result['inspected_count'],2)
        self.assertEqual(self.batch(first,loading_actions=1,elapsed_seconds=4),result)
        state=self.app.execute('run-status',{'run_id':self.run})
        self.assertEqual((state['loads'],state['elapsed_seconds']),(1,4))
        for i in range(3):
            result=self.batch(first,batch_id=f'repeat-{i}',loading_actions=1)
        self.assertEqual(result['stop_reason'],'no_progress')

    def test_unrelated_posts_are_progress_without_retaining_content(self):
        for i in range(4):
            result=self.batch([self.skip(str(i))],batch_id=str(i),loading_actions=1)
        self.assertIsNone(result['stop_reason'])
        self.assertEqual(result['new_candidates'],0)
        self.assertEqual(self.app.all('post'),[])
        self.assertTrue(all('post' not in o and 'content' not in o for o in self.app.all('feed-observation')))
        self.batch([],batch_id='initial-empty',loading_actions=0)
        self.assertEqual(self.app.get('run',self.run)['stalled'],0)

    def test_invalid_batch_rollback_and_source_contract(self):
        with self.assertRaises(ValueError): self.batch([self.candidate(),dict(disposition='candidate',reason='missing source')])
        self.assertEqual(self.app.all('feed-observation'),[])
        with self.assertRaises(ValueError): self.batch([self.skip(str(i)) for i in range(11)])
        with self.assertRaises(ValueError): self.batch([],loading_actions=-1)
        with self.assertRaises(ValueError): self.batch([],elapsed_seconds=float('inf'))
        with self.assertRaises(ValueError): self.app.execute('ingest-posts',{'run_id':self.run,'posts':[]})
        self.run=self.start(collection_source='search')
        with self.assertRaises(ValueError): self.batch([])

    def test_conflicting_batch_does_not_mutate_counts(self):
        self.batch([self.skip('one')])
        with self.assertRaises(ValueError): self.batch([self.skip('two')])
        self.assertEqual(self.app.execute('run-status',{'run_id':self.run})['inspected_count'],1)

    def test_fallback_permalink_does_not_increment_feed_count(self):
        item=self.candidate()
        item['post']['url']=''
        self.batch([item])
        result=self.batch([self.candidate()],batch_id='permalink')
        self.assertEqual(result['inspected_count'],1)
        self.assertEqual(result['new_candidates'],1)
        self.assertEqual(len(self.app.all('post')),1)
        self.assertEqual(self.app.all('post')[0]['url'],self.candidate()['post']['url'])
        self.run=self.start()
        fallback=self.candidate('20',content='Different synthetic role')
        fallback['post']['url']=''
        result=self.batch([fallback,self.candidate('20',content='Different synthetic role'),self.candidate('21',content='Different synthetic role')])
        self.assertEqual(result['inspected_count'],2)
        self.assertEqual(result['new_candidates'],2)

    def test_restart_and_cross_source_history(self):
        self.run=self.start(collection_source='search')
        post=self.candidate()['post']
        self.app.execute('ingest-posts',{'run_id':self.run,'posts':[post],'loading_actions':0})
        evidence=self.app.execute('save-evidence',{'post_id':'10','source_url':post['url'],'quote':post['content']})['evidence_id']
        assessment=dict(post_id='10',content_digest=self.app.get('post','10')['content_digest'],role='Researcher',company='Example',
                        checks={k:dict(result='pass',evidence_ids=[evidence]) for k in (*CHECKS,'location','title')},
                        scores=dict(role=30,skills=30,experience=20,education=15),resume_id='tech',resume_evidence=['Python research PhD'],
                        explanation='Synthetic fit',message=' '.join(['word']*80))
        lead=self.app.execute('save-assessments',{'run_id':self.run,'assessments':[assessment]})[0]['lead_id']
        self.app.execute('update-lead',{'lead_id':lead,'edits':{'status':'applied'}})
        self.run=self.start()
        result=self.batch([self.candidate()])
        self.assertEqual((result['inspected_count'],result['new_candidates']),(1,0))
        self.app.db.close()
        self.app=Hunter(self.root/'data')
        result=self.batch([self.candidate(),self.skip('other')],batch_id='resume')
        self.assertEqual(result['inspected_count'],2)
        self.assertEqual(self.app.execute('list-leads',{'new_only':True}),[])
        self.assertEqual({x['source'] for x in self.app.all('post-sighting')},{'search','for_you'})
        self.run=self.start()
        self.assertEqual(self.batch([self.candidate()])['inspected_count'],1)
        self.assertEqual(len(self.app.all('post')),1)
        self.run=self.start()
        self.batch([self.candidate(content='Edited role requirements')])
        self.assertEqual(self.app.get('lead',lead)['status'],'applied')
        self.assertTrue(self.app.get('lead',lead)['stale'])

    def test_limits_and_plan_does_not_apply_search_filters(self):
        plan=self.app.execute('search-plan',{'config':self.config})
        self.assertEqual(plan['lanes'],[])
        self.assertNotIn('sort_by',plan)
        for config, reason in [({'max_inspected':1},'inspection_limit'),({'max_loading_actions':1},'loading_limit'),({'max_minutes':1},'time_limit')]:
            self.run=self.start(**config)
            result=self.batch([self.skip('one')],loading_actions=1,elapsed_seconds=60 if 'max_minutes' in config else 0)
            self.assertEqual(result['stop_reason'],reason)
        for value in (0,501,True):
            with self.assertRaises(ValueError): self.start(feed_post_count=value)

    def test_workbook_feed_counts_and_source(self):
        self.batch([self.candidate(),self.skip('not-hiring'),self.skip('ad','sponsored')])
        path=self.app.execute('sync-workbook',{})['path']
        book=load_workbook(path)
        try:
            rows=list(book['Runs'].values)
            run=dict(zip(rows[0],rows[1]))
            self.assertEqual(run['collection_source'],'for_you')
            self.assertEqual(run['inspected_count'],'3')
            rows=list(book['Candidates'].values)
            candidate=dict(zip(rows[0],rows[1]))
            self.assertEqual(candidate['discovery_sources'],'for_you')
            self.assertEqual(candidate['post_id'],'10')
        finally:
            book.close()


if __name__ == '__main__':
    unittest.main()
