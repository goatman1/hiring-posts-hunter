import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.agents/skills/job-search/scripts'))
from job_hunter import Hunter
from discovery import MANAGER_CHECKS, ELIGIBILITY_CHECKS


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Hunter(self.temp.name)
        self.protocol = dict(comparison_id='pilot', arms={'broad': 'hiring ML', 'intent': 'my team ML'},
                             track='tech', sort_by='relevance', date_posted='past_month',
                             budget=dict(posts=2, profiles=1, jobs=1))
        self.app.execute('start-comparison', self.protocol)

    def tearDown(self):
        self.app.db.close()
        self.temp.cleanup()

    def observation(self):
        profile = 'https://example.com/in/manager'
        post = 'https://example.com/post/1'
        return dict(post_key='1', rank=1, author_url=profile, source_url=post, excerpt='My team hires ML scientists',
                    promising=True, reason='Relevant team hiring', checks={k:dict(result='pass', source_url=profile if k in ('author_us','manager','affiliation') else post,
                    quote='Synthetic supporting quote', reason='Synthetic evidence interpretation') for k in ELIGIBILITY_CHECKS})

    def arm(self):
        return dict(comparison_id='pilot', arm='broad', observations=[self.observation()],
                    profiles_used=['https://example.com/in/manager'], jobs_used=[], stop_reason='exhausted',
                    observed_filters='Top Match; Past month')

    def test_cross_arm_overlap_and_unknowns(self):
        first = self.arm()
        self.app.execute('save-comparison-arm', first)
        self.app.execute('save-comparison-arm', first)
        second = copy.deepcopy(first)
        second['arm'] = 'intent'
        second['observations'][0]['checks']['entry_level'] = {'result':'unknown'}
        self.app.execute('save-comparison-arm', second)
        report = self.app.execute('comparison-report', {'comparison_id':'pilot'})
        self.assertEqual(report['post_overlap']['broad / intent'], 1)
        self.assertEqual(report['arms']['broad']['eligible_posts'], 1)
        self.assertEqual(report['arms']['intent']['eligible_posts'], 0)
        self.assertEqual(report['arms']['intent']['verified_us_managers'], 1)
        self.assertEqual(report['arms']['intent']['unresolved_promising'], 1)

    def test_manager_is_not_own_team_and_job_country_not_author_country(self):
        for check in ('own_team','author_us','manager','affiliation'):
            arm=self.arm()
            arm['comparison_id']=check
            protocol={**self.protocol,'comparison_id':check}
            self.app.execute('start-comparison',protocol)
            arm['observations'][0]['checks'][check]={'result':'unknown'}
            self.app.execute('save-comparison-arm',arm)
            result=self.app.execute('comparison-report',{'comparison_id':check})
            self.assertEqual(result['arms']['broad']['verified_us_managers'],0)

    def test_action_caps_duplicates_and_rank_order(self):
        arm=self.arm()
        cases=[]
        extra=copy.deepcopy(arm); extra['profiles_used']*=2; cases.append(extra)
        extra=copy.deepcopy(arm); extra['jobs_used']=['https://example.com/j/1','https://example.com/j/2']; cases.append(extra)
        extra=copy.deepcopy(arm); extra['observations']*=2; cases.append(extra)
        extra=copy.deepcopy(arm); extra['observations'][0]['rank']=2; cases.append(extra)
        for extra in cases:
            with self.assertRaises(ValueError): self.app.execute('save-comparison-arm',extra)
        self.assertEqual(self.app.all('comparison-arm'),[])

    def test_evidence_and_cached_checks_are_charged(self):
        arm=self.arm(); arm['profiles_used']=[]
        with self.assertRaises(ValueError): self.app.execute('save-comparison-arm',arm)
        arm=self.arm(); arm['observations'][0]['checks']['full_time']['source_url']='https://example.com/job/1'
        with self.assertRaises(ValueError): self.app.execute('save-comparison-arm',arm)
        arm['jobs_used']=['https://example.com/job/1']
        self.app.execute('save-comparison-arm',arm)

    def test_immutable_protocol_audit_and_incomplete(self):
        self.app.execute('start-comparison',self.protocol)
        changed={**self.protocol,'track':'quant'}
        with self.assertRaises(ValueError): self.app.execute('start-comparison',changed)
        arm=self.arm(); self.app.execute('save-comparison-arm',arm)
        arm['observations'][0]['reason']='Changed audit'
        with self.assertRaises(ValueError): self.app.execute('save-comparison-arm',arm)
        report=self.app.execute('comparison-report',{'comparison_id':'pilot'})
        self.assertEqual(report['arms']['intent']['status'],'incomplete')

    def test_distinct_authors_not_post_count(self):
        arm=self.arm(); second=copy.deepcopy(arm['observations'][0]); second.update(rank=2,post_key='2')
        arm['observations'].append(second)
        self.app.execute('save-comparison-arm',arm)
        report=self.app.execute('comparison-report',{'comparison_id':'pilot'})['arms']['broad']
        self.assertEqual(report['inspected'],2)
        self.assertEqual(report['verified_us_managers'],1)

    def test_author_cache_freshness_history_and_conflict(self):
        record=dict(author_url='https://example.com/in/person/?ref=search',employer='Example',
                    checked_at=(datetime.now(timezone.utc)-timedelta(days=31)).isoformat(),
                    checks={k:dict(result='unknown') for k in ('author_us','manager','affiliation')})
        self.app.execute('save-author',record)
        request={'author_url':'https://example.com/in/person'}
        self.assertTrue(self.app.execute('get-author',request)['revalidate'])
        old=copy.deepcopy(record)
        record['checked_at']=datetime.now(timezone.utc).isoformat()
        self.app.execute('save-author',record)
        self.app.execute('save-author',old)
        self.assertFalse(self.app.execute('get-author',request)['revalidate'])
        self.assertTrue(self.app.execute('get-author',{**request,'expected_employer':'Changed'})['revalidate'])
        self.assertTrue(self.app.execute('get-author',{**request,'contradiction':True})['revalidate'])
        self.assertEqual(len(self.app.all('author-evidence')),2)
        record['checks']['own_team']={'result':'pass'}
        with self.assertRaises(ValueError): self.app.execute('save-author',record)

    def test_search_plan_scopes_modes_overrides(self):
        default=self.app.execute('search-plan',{})
        self.assertEqual(default['sort_by'],'date_posted')
        self.assertTrue(default['lanes'][-1]['requires_scope'])
        discovery=self.app.execute('search-plan',{'config':{'search_phase':'discovery'}})
        self.assertEqual((discovery['sort_by'],discovery['date_posted']),('relevance','past_month'))
        explicit=self.app.execute('search-plan',{'config':{'search_phase':'discovery','sort_by':'date_posted','target_companies':['Example']}})
        self.assertEqual(explicit['sort_by'],'date_posted')
        self.assertFalse(explicit['lanes'][-1]['requires_scope'])
        with self.assertRaises(ValueError): self.app.execute('search-plan',{'config':{'search_strategy':'magic'}})


if __name__ == '__main__':
    unittest.main()
