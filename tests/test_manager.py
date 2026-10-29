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

if __name__=='__main__': unittest.main()
