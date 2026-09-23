import tempfile
import unittest
from pathlib import Path
from video_workflow.engine import *

def fixture(): return Job('Demo','script','persona',[Shot('a',2,'a','hello')],0),[Asset('a','card',('a',),'SELF')]
class WorkflowTests(unittest.TestCase):
    def test_01_valid(self):validate(fixture()[0])
    def test_02_missing_title(self):j,_=fixture();j.title='';self.assertRaises(ValueError,validate,j)
    def test_03_missing_script(self):j,_=fixture();j.script='';self.assertRaises(ValueError,validate,j)
    def test_04_missing_persona(self):j,_=fixture();j.persona='';self.assertRaises(ValueError,validate,j)
    def test_05_missing_shots(self):j,_=fixture();j.shots=[];self.assertRaises(ValueError,validate,j)
    def test_06_zero_duration(self):j,_=fixture();j.shots[0]=Shot('a',0,'a','x');self.assertRaises(ValueError,validate,j)
    def test_07_duplicate_shot(self):j,_=fixture();j.shots*=2;self.assertRaises(ValueError,validate,j)
    def test_08_negative_budget(self):j,_=fixture();j.budget_usd=-1;self.assertRaises(ValueError,validate,j)
    def test_09_retrieve(self):j,a=fixture();self.assertEqual(retrieve(j.shots,a)[1],[])
    def test_10_gap(self):j,a=fixture();self.assertEqual(retrieve(j.shots,[])[1],['a'])
    def test_11_disallow_unlicensed(self):j,a=fixture();self.assertEqual(retrieve(j.shots,[Asset('x','card',('a',),'UNKNOWN')])[1],['a'])
    def test_12_disallow_nonsynthetic(self):j,a=fixture();self.assertEqual(retrieve(j.shots,[Asset('x','card',('a',),'SELF',False)])[1],['a'])
    def test_13_external_unconfigured(self):j,a=fixture();self.assertRaises(RuntimeError,ExternalProviderInterface().render,j,a,Path('x'))
    def test_14_gap_stops(self):j,_=fixture();self.assertEqual(run(j,[],MockProvider(),Path('x'))['state'],'GAP')
    def test_15_mock_output(self):
        j,a=fixture()
        with tempfile.TemporaryDirectory() as d:self.assertEqual(run(j,a,MockProvider(),Path(d)/'o.json')['state'],'HUMAN_REVIEW')
    def test_16_qa_missing_output(self):j,_=fixture();self.assertIn('OUTPUT_MISSING',qa(j))
    def test_17_qa_duration(self):j,_=fixture();j.shots=[Shot('a',61,'a','x')];self.assertIn('DURATION_EXCEEDS_DEMO_LIMIT',qa(j))
    def test_18_qa_budget(self):j,_=fixture();j.cost_usd=1;self.assertIn('BUDGET_EXCEEDED',qa(j))
    def test_19_qa_narration(self):j,_=fixture();j.shots=[Shot('a',2,'a','')];self.assertIn('NARRATION_MISSING',qa(j))
    def test_20_review_required(self):j,_=fixture();self.assertRaises(ValueError,approve,j,'someone')
    def test_21_reviewer_required(self):j,_=fixture();j.state=State.HUMAN_REVIEW;self.assertRaises(ValueError,approve,j,'')
    def test_22_approve(self):j,_=fixture();j.state=State.HUMAN_REVIEW;approve(j,'Human');self.assertEqual(j.state,State.APPROVED)
    def test_23_render_failure(self):j,a=fixture();self.assertEqual(run(j,a,ExternalProviderInterface(),Path('x'))['state'],'FAILED')
    def test_24_retry_count(self):j,a=fixture();run(j,a,ExternalProviderInterface(),Path('x'));self.assertEqual(j.retries,1)
if __name__=='__main__':unittest.main()
