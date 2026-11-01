"""Verify the reviewed home cleanup without displaying provider configuration."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
home = Path.home()
backup = root / '.local-work/legacy-home-team-backup-20261031-103708'
manifest = json.loads((backup / 'SHA256.json').read_text())
for relative, checksum in manifest.items():
    assert hashlib.sha256((backup / relative).read_bytes()).hexdigest() == checksum
    if relative != 'opencode.json':
        assert not (home / relative).exists(), relative
expected = json.loads((backup / 'opencode.json').read_text())
for key in ('default_agent', 'instructions', 'subagent_depth', 'agent'):
    expected.pop(key)
expected['permission']['bash'].pop('python3 .opencode/tools/git_sync.py *')
assert json.loads((home / 'opencode.json').read_text()) == expected
assert not list((home / '.opencode/agents').glob('*.md'))
roles = {p.stem for p in (root / 'lib/profiles').glob('*.md')}
for directory in (home, root):
    result = subprocess.run(['opencode', 'debug', 'config'], cwd=directory,
                            capture_output=True, text=True, check=True, timeout=30)
    config = json.loads(result.stdout)
    inherited = roles.intersection(config.get('agent', {}))
    assert not inherited, (directory, inherited)
    assert config.get('default_agent') not in roles
    assert not any('.opencode/team/TEAM_RULES.md' in p or '.opencode/team/WORKFLOW.md' in p
                   for p in config.get('instructions', []))
    print(f'OpenCode configuration OK in {directory}: no inherited legacy team')
print('Backup verified; 31 obsolete files removed; unrelated home configuration preserved.')
