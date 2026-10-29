import importlib.util, json, sys, tempfile, unittest
from pathlib import Path
LIB=Path(__file__).resolve().parents[1]/'lib'
sys.path.insert(0,str(LIB))
import manager as mgr
from access_check import path_decision,url_decision,validate,load_policy
BASE={'shell':'ask','file_edit':'allow','outside_read':'deny','outside_write':'deny',
      'gitpush':'deny','internet':'deny','secrets':'deny','sudo':'deny','destructive':'deny','unattended':False,
      'mcp':'deny','packages':'deny','hardware':'deny','mounts':[]}

class AccessPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.project=Path(self.temp.name)/'project';self.project.mkdir()
        self.policy=mgr.default_access_policy(self.project,BASE)
    def tearDown(self): self.temp.cleanup()
    def test_root_default_and_project_allow(self):
        self.assertEqual(path_decision(self.policy,str(self.project/'src.py'),'read'),'allow')
        self.assertEqual(path_decision(self.policy,'/etc/passwd','read'),'deny')
        self.assertEqual(path_decision(self.policy,'/tmp/file','write'),'deny')
        self.assertEqual(url_decision(self.policy,'https://example.org/a'),'deny')
    def test_path_whitelist_and_nested_blacklist(self):
        allowed=Path(self.temp.name)/'share'
        self.policy['filesystem']['paths']=[
          {'path':str(allowed),'kind':'network-share','read':'allow','write':'deny'},
          {'path':str(allowed/'private'),'kind':'network-share','read':'deny','write':'deny'}]
        self.assertEqual(path_decision(self.policy,str(allowed/'public/doc.txt'),'read'),'allow')
        self.assertEqual(path_decision(self.policy,str(allowed/'public/doc.txt'),'write'),'deny')
        self.assertEqual(path_decision(self.policy,str(allowed/'private/key.txt'),'read'),'deny')
    def test_root_explicit_allow_refused(self):
        self.policy['filesystem']['paths'].append({'path':'/','read':'allow','write':'allow'})
        with self.assertRaises(ValueError):validate(self.policy)
    def test_urls_scheme_and_host(self):
        self.policy['network']['hosts']=[{'host':'docs.python.org','scheme':'https','access':'allow'},
            {'host':'*.example.org','scheme':'https','access':'allow'},
            {'host':'blocked.example.org','scheme':'https','access':'deny'}]
        self.assertEqual(url_decision(self.policy,'https://docs.python.org/3/'),'allow')
        self.assertEqual(url_decision(self.policy,'http://docs.python.org/'),'deny')
        self.assertEqual(url_decision(self.policy,'https://docs.python.org.attacker.com/'),'deny')
        self.assertEqual(url_decision(self.policy,'https://sub.example.org/'),'allow')
        self.assertEqual(url_decision(self.policy,'https://blocked.example.org/'),'deny')
    def test_open_code_permissions_not_overbroad_webfetch(self):
        self.policy['network']['hosts']=[{'host':'docs.python.org','scheme':'https','access':'allow'}]
        cfg=mgr.make_permission({**BASE,'_selected_agents':['orchestrator']},self.policy)
        self.assertEqual(cfg['webfetch'],'deny')
        self.assertEqual(cfg['websearch'],'deny')
        self.assertEqual(cfg['external_directory']['*'],'deny')
        self.assertNotIn('/tmp/**', cfg['external_directory'])
        self.assertEqual(cfg['edit']['AGENT_ACCESS_POLICY.json'],'deny')
        self.assertEqual(cfg['edit'][str(self.project/'AGENT_ACCESS_POLICY.json')],'deny')
        self.assertEqual(cfg['read'][str(self.project)+'/**'],'allow')
        self.assertEqual(cfg['bash']['python3 .opencode/tools/access_fetch.py *'],'allow')
    def test_full_install_and_sync_retain_models(self):
        self.project.joinpath('AGENTS.md').write_text('My instructions\n')
        self.project.joinpath('opencode.json').write_text(json.dumps({'model':'my/model','small_model':'my/small'}))
        mgr.apply(self.project,['orchestrator'],{'orchestrator':'my/model'},BASE,'SHAREABLE')
        cfg=json.loads((self.project/'opencode.json').read_text())
        self.assertIn(mgr.ACCESS_RULES,cfg['instructions'])
        self.assertTrue((self.project/mgr.ACCESS_FILE).exists())
        self.assertTrue((self.project/'.opencode/tools/access_fetch.py').exists())
        self.assertIn('NOT ACTUAL SECURITY',(self.project/mgr.ACCESS_RULES).read_text())
        policy=json.loads((self.project/mgr.ACCESS_FILE).read_text())
        policy['filesystem']['paths'].append({'path':'/mnt/datasets','kind':'local','read':'allow','write':'deny'})
        self.project.joinpath(mgr.ACCESS_FILE).write_text(json.dumps(policy))
        mgr.sync_access(self.project)
        cfg=json.loads((self.project/'opencode.json').read_text())
        self.assertEqual(cfg['model'],'my/model')
        self.assertEqual(cfg['small_model'],'my/small')
        self.assertEqual(cfg['permission']['read']['/mnt/datasets/**'],'allow')
        self.assertEqual(cfg['permission']['edit']['/mnt/datasets/**'],'deny')
        self.assertIn('My instructions',(self.project/'AGENTS.md').read_text())
        self.assertIn('AGENT_ACCESS_POLICY.json',(self.project/'AGENTS.md').read_text())
    def test_vm_override_visible(self):
        self.policy['filesystem']['default_outside']={'read':'allow','write':'allow'}
        self.assertIn('BROAD ACCESS EXCEPTION',mgr.render_access_rules(self.policy))

if __name__=='__main__':unittest.main()
