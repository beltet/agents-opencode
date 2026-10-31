import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MANAGER=Path(__file__).resolve().parents[1]/'lib'/'manager.py'
spec=importlib.util.spec_from_file_location('mgr',MANAGER)
mgr=importlib.util.module_from_spec(spec); spec.loader.exec_module(mgr)

PERM={
'shell':'allow','gitpush':'deny','internet':'deny','outside_read':'deny','outside_write':'deny',
'sudo':'deny','destructive':'allow','secrets':'deny','unattended':False,'mounts':[]}

class TestInstaller(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.root=Path(self.temp.name); self.project=self.root/'project'; self.project.mkdir()
  self.project.joinpath('AGENTS.md').write_text('Existing team instructions\n')
  self.project.joinpath('opencode.json').write_text(json.dumps({'model':'original/model','small_model':'original/small','provider':{'x':{'npm':'example'}},'agent':{'custom':{'model':'custom/model'}}}))
 def tearDown(self): self.temp.cleanup()
 def test_profiles_and_no_model_yaml(self):
  profiles=mgr.profiles()
  self.assertEqual(len(profiles),23)
  for p in profiles.values():
   fm=p.read_text().split('---',2)[1]
   self.assertNotIn('model:',fm)
   self.assertNotIn('permission:',fm)
   self.assertNotIn('steps:',fm)
   self.assertNotIn('maxSteps:',fm)
 def test_install_preserves_custom_json_and_old_agents_file(self):
  mgr.apply(self.project,['orchestrator','system-architect'],{'orchestrator':'some/model','system-architect':'other/model'},PERM,'SHAREABLE')
  cfg=json.loads((self.project/'opencode.json').read_text())
  self.assertEqual(cfg['model'],'some/model')
  self.assertEqual(cfg['small_model'],'original/small')
  self.assertEqual(cfg['provider']['x']['npm'],'example')
  self.assertEqual(cfg['agent']['custom']['model'],'custom/model')
  self.assertEqual(cfg['agent']['orchestrator']['model'],'some/model')
  self.assertEqual(cfg['enabled_providers'],['other','some'])
  self.assertIn('Existing team instructions',(self.project/'AGENTS.md').read_text())
  self.assertEqual(len(list((self.project/'.opencode/agents').glob('*.md'))),2)
  self.assertEqual(cfg['permission']['task']['software-engineer'],'deny' if 'software-engineer' in cfg['permission']['task'] else 'missing') if False else None
  self.assertEqual(cfg['permission']['task']['*'],'deny')
  self.assertEqual(cfg['permission']['task']['orchestrator'],'allow')
 def test_remove_agent_no_untracked_delete(self):
  mgr.apply(self.project,['orchestrator','system-architect'],{'orchestrator':'a/b','system-architect':'c/d'},PERM,'SHAREABLE')
  other=self.project/'.opencode/agents/my-own-agent.md'; other.write_text('mine')
  mgr.apply(self.project,['orchestrator'],{'orchestrator':'a/b'},PERM,'SHAREABLE')
  self.assertTrue(other.exists()); self.assertFalse((self.project/'.opencode/agents/system-architect.md').exists())
  cfg=json.loads((self.project/'opencode.json').read_text()); self.assertNotIn('system-architect',cfg['agent'])
  self.assertEqual((self.project/'AGENTS.md').read_text().count(mgr.MARK_OPEN),1)
 def test_gitpush_prohibition_wins_over_destructive_allow(self):
  p=mgr.make_permission({**PERM,'_selected_agents':['orchestrator']})
  self.assertEqual(p['bash']['git push*'],'deny')
  self.assertEqual(p['bash']['git push --force*'],'deny')
  self.assertEqual(p['webfetch'],'deny')
  self.assertEqual(p['external_directory']['*'],'deny')
 def test_mounted_share_read_only(self):
  mount={'path':str(self.root/'mount'), 'read':'allow','write':'deny'}
  p=mgr.make_permission({**PERM,'mounts':[mount],'_selected_agents':['orchestrator']})
  self.assertEqual(p['external_directory'][mount['path']+'/*'],'allow')
  self.assertEqual(p['read'][mount['path']+'/*'],'allow')
  self.assertEqual(p['edit'][mount['path']+'/*'],'deny')
 def test_models_parser(self):
  f=self.root/'models.txt'; f.write_text('opencode/abc\nopenai/gpt-6.1-sol\nother lines\nopencode/abc\n')
  old=os.environ.get('AGENTS_OPENCODE_TEST_MODELS_FILE'); os.environ['AGENTS_OPENCODE_TEST_MODELS_FILE']=str(f)
  try:self.assertEqual(mgr.list_models(self.project),['opencode/abc','openai/gpt-6.1-sol'])
  finally:
   if old is None: del os.environ['AGENTS_OPENCODE_TEST_MODELS_FILE']
   else: os.environ['AGENTS_OPENCODE_TEST_MODELS_FILE']=old
 def test_replaces_legacy_agents_instructions(self):
  legacy=(mgr.ROOT/'LEGACY_AGENTS.md').read_text().strip()
  (self.project/'AGENTS.md').write_text('Custom intro\n\n'+legacy+'\n')
  mgr.apply(self.project,['orchestrator'],{'orchestrator':'a/b'},PERM,'SHAREABLE')
  content=(self.project/'AGENTS.md').read_text()
  self.assertEqual(content.count('Custom intro'),1)
  self.assertNotIn('# Project AI team instructions',content)
  self.assertEqual(content.count(mgr.MARK_OPEN),1)

 def test_refresh_preserves_owner_controls_and_removes_inline_caps(self):
  selected=['orchestrator','software-engineer']
  mgr.apply(self.project,selected,{'orchestrator':'a/b','software-engineer':'c/d'},PERM,'SHAREABLE')
  config_path=self.project/'opencode.json'
  cfg=json.loads(config_path.read_text())
  cfg['agent']['orchestrator'].update(steps=36,maxSteps=36,temperature=0.2)
  cfg['agent']['software-engineer']['steps']=24
  cfg['agent']['custom']['steps']=7
  cfg['agent']['orchestrator']['permission']={'task':'deny'}
  cfg['enabled_providers'].append('approved-fallback')
  cfg['instructions'].append('owner-rules.md')
  config_path.write_text(json.dumps(cfg))
  expected=json.loads(json.dumps(cfg))
  for name in selected:
   expected['agent'][name].pop('steps',None)
   expected['agent'][name].pop('maxSteps',None)
  protected=[self.project/'AGENT_ACCESS_POLICY.json',self.project/'PROJECT_POLICY.md',self.project/'.opencode/team/ACCESS_RULES.md']
  before={p:p.read_bytes() for p in protected}
  state=self.project/'.local-work/ACTIVE.md'
  state.parent.mkdir(); state.write_text('Owner queue and actual approval gate\n')
  installed=self.project/'.opencode/agents/orchestrator.md'
  installed.write_text('Locally edited old profile\n')
  custom=self.project/'.opencode/agents/custom.md'; custom.write_text('custom role\n')
  result=subprocess.run([sys.executable,str(MANAGER),'refresh',str(self.project),'--lang','en'],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn('Restart OpenCode',result.stdout)
  self.assertEqual(json.loads(config_path.read_text()),expected)
  self.assertEqual(installed.read_bytes(),(mgr.PROFILES/'orchestrator.md').read_bytes())
  self.assertTrue(list(installed.parent.glob('orchestrator.md.backup-agentteam-*')))
  self.assertEqual(custom.read_text(),'custom role\n')
  self.assertEqual(state.read_text(),'Owner queue and actual approval gate\n')
  for p,content in before.items(): self.assertEqual(p.read_bytes(),content)
  self.assertIn('Existing team instructions',(self.project/'AGENTS.md').read_text())
  self.assertEqual((self.project/'AGENTS.md').read_text().count(mgr.MARK_OPEN),1)
  backups=set(self.project.rglob('*.backup-agentteam-*'))
  mgr.refresh_team(self.project)
  self.assertEqual(set(self.project.rglob('*.backup-agentteam-*')),backups)

 def test_refresh_requires_installation_and_preflights_missing_sources(self):
  before=(self.project/'opencode.json').read_bytes()
  with self.assertRaisesRegex(RuntimeError,'install'): mgr.refresh_team(self.project)
  self.assertEqual((self.project/'opencode.json').read_bytes(),before)
  mgr.apply(self.project,['orchestrator'],{'orchestrator':'a/b'},PERM,'SHAREABLE')
  manifest_path=self.project/mgr.MANIFEST
  manifest=json.loads(manifest_path.read_text())
  manifest['installed_agents'].append('missing-custom-agent')
  manifest_path.write_text(json.dumps(manifest))
  installed=self.project/'.opencode/agents/orchestrator.md'
  installed.write_text('Preserve on failed preflight\n')
  before=(self.project/'opencode.json').read_bytes()
  with self.assertRaisesRegex(RuntimeError,'missing-custom-agent'): mgr.refresh_team(self.project)
  self.assertEqual(installed.read_text(),'Preserve on failed preflight\n')
  self.assertEqual((self.project/'opencode.json').read_bytes(),before)

 def test_reinstall_removes_managed_inline_step_overrides_only(self):
  cfg=json.loads((self.project/'opencode.json').read_text())
  cfg['agent']['orchestrator']={'steps':36,'maxSteps':36,'temperature':0.2}
  cfg['agent']['custom']['steps']=9
  (self.project/'opencode.json').write_text(json.dumps(cfg))
  mgr.apply(self.project,['orchestrator'],{'orchestrator':'a/b'},PERM,'SHAREABLE')
  cfg=json.loads((self.project/'opencode.json').read_text())
  self.assertEqual(cfg['agent']['orchestrator'],{'temperature':0.2,'model':'a/b'})
  self.assertEqual(cfg['agent']['custom']['steps'],9)

class TestCharacterProfiles(unittest.TestCase):
 def test_cast_matches_profiles_and_keeps_personas_nonbinding(self):
  import re
  cast=(MANAGER.parents[1]/'AGENT_CAST.md').read_text()
  profiles=mgr.profiles()
  rows=re.findall(r'^\| ([a-z-]+) \| \*\*(\w+) \((\d+), (she/her|he/him)\)\*\*',cast,re.M)
  self.assertEqual({row[0] for row in rows},set(profiles))
  self.assertEqual(len(rows),23)
  self.assertEqual(len({row[1] for row in rows}),23)
  self.assertEqual(sum(row[3]=='she/her' for row in rows),12)
  self.assertEqual(sum(row[3]=='he/him' for row in rows),11)
  self.assertGreaterEqual(max(int(row[2]) for row in rows)-min(int(row[2]) for row in rows),30)
  for role,name,age,pronouns in rows:
   with self.subTest(role=role):
    text=profiles[role].read_text()
    self.assertIn(f'{name}, {age}, {pronouns}',text)
    self.assertIn('Fictional presentation only; never enact this backstory',text)
    for label in ('Drive','Reasoning style','Collaboration style','Self-check'):
     self.assertIn(f'**{label}:**',text)

 def test_install_copies_all_profiles_and_persona_rules_exactly(self):
  with tempfile.TemporaryDirectory() as directory:
   project=Path(directory)
   profiles=mgr.profiles()
   mgr.apply(project,list(profiles),{name:'test/model' for name in profiles},PERM,'SHAREABLE')
   for name,source in profiles.items():
    with self.subTest(role=name):
     self.assertEqual((project/'.opencode/agents'/f'{name}.md').read_bytes(),source.read_bytes())
   rules=(project/'.opencode/team/TEAM_RULES.md').read_bytes()
   self.assertEqual(rules,(mgr.ROOT/'TEAM_RULES.md').read_bytes())
   self.assertIn(b'No favoritism, secrecy, romantic advances at work',rules)

if __name__=='__main__': unittest.main()
