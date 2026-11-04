"""Static workflow checks don't prove the agent will obey; they prevent contradictory instructions."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class WorkflowContract(unittest.TestCase):
    def read(self,s):return (ROOT/s).read_text(encoding='utf-8')

    def test_start_links_one_agent_skills(self):
        s=self.read('prompts/SCENARIO.md')
        for p in ('cofa-triage','cofa-decide','cofa-build','cofa-verify','cofa-explain'):
            self.assertIn(p,s)
        self.assertIn('하나의 Codex',s)
        self.assertIn('한 번에 한 결정',s)

    def test_business_questions_required_in_initial_triage(self):
        triage=self.read('skills/cofa-triage/SKILL.md')
        for marker in ('현업 확인 질문 목록', '초기 분석의 필수 산출물', 'Q-ID', 'P0/P1/P2', '답변에 따라 달라지는 구현', '현업 확인 질문 없음', '한 번에 보여주되'):
            self.assertIn(marker,triage,marker)
        self.assertIn('이미 답이 확정된 질문',triage)

    def test_question_list_handoff_and_single_decision(self):
        scenario=self.read('prompts/SCENARIO.md')
        start=self.read('prompts/START.md')
        for marker in ('현업 확인 질문 목록', '첫 분석 결과', 'P0/P1/P2', '현업 확인 질문 없음', '한 번에 한 결정'):
            self.assertIn(marker,scenario,marker)
        self.assertIn('현업 확인 질문 목록',start)
        self.assertIn('한 건씩',start)
        self.assertIn('현업 확인 질문 목록',self.read('README.md'))

    def test_no_subagent_configs_or_installers(self):
        self.assertFalse((ROOT/'.codex').exists())
        self.assertFalse((ROOT/'skills/cofa-delegate').exists())
        for n in ('apply_final.py','BUILD_COMPLETE.cmd','base_v2','payload'):
            self.assertFalse((ROOT/n).exists(),n)

    def test_decision_skill_requires_one_question(self):
        s=self.read('skills/cofa-decide/SKILL.md')
        self.assertIn('한 개만',s)
        self.assertNotIn('1~3개',s)

    def test_no_approval_from_uat(self):
        for p in ('prompts/SCENARIO.md','prompts/UAT.md','skills/cofa-verify/SKILL.md'):
            s=self.read(p)
            self.assertTrue('정책 승인' in s or '정책 결정' in s,p)
            self.assertIn('PASS',s,p)

    def test_actual_task_and_example_distinguished(self):
        s=self.read('prompts/SCENARIO.md')
        self.assertIn('실제 과제 README',s)
        self.assertIn('공식',self.read('examples/shuttle/README.md'))

    def test_all_core_files_exist(self):
        for p in ['README.md','AGENTS.md','QUICKSTART.md','scripts/decision_log.py','scripts/source_guard.py',
                  'scripts/data_tools.py','examples/shuttle/verify_routes.py','examples/joins/expected.json',
                  'examples/semiconductor/expected.json']:
            self.assertTrue((ROOT/p).is_file(),p)

    def test_mandatory_dropped_not_a_pass(self):
        for p in ['AGENTS.md','README.md','prompts/SCENARIO.md','skills/cofa-verify/SKILL.md']:
            self.assertIn('dropped',self.read(p).lower(),p)

    def test_gui_no_auto_browsing(self):
        for p in ['prompts/UAT.md','AGENTS.md','skills/cofa-verify/SKILL.md']:
            self.assertIn('Browser',self.read(p),p)

if __name__=='__main__':unittest.main()
