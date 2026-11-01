"""One-off, owner-approved backup of the reviewed legacy home team files."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
home = Path.home()
roles = sorted(p.stem for p in (root / 'lib/profiles').glob('*.md'))
paths = [Path('.opencode/agents') / (name + '.md') for name in roles]
paths += [Path('.opencode/team') / name for name in
          ('TEAM_RULES.md', 'WORKFLOW.md', 'HANDOFF_TEMPLATE.md')]
paths += [Path('.opencode/tools') / name for name in ('git_sync.py', 'model_manager.py')]
paths += [Path(name) for name in ('AGENTS.md', 'PROJECT_POLICY.md',
                                'PROJECT_RUNTIME_POLICY.json', 'opencode.json')]
for relative in paths:
    source = home / relative
    if source.is_symlink() or not source.is_file():
        raise RuntimeError(f'Expected reviewed regular file: {source}')
destination = root / '.local-work' / ('legacy-home-team-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
destination.mkdir(mode=0o700)
manifest = {}
for relative in paths:
    source, target = home / relative, destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == original
    manifest[str(relative)] = original
(destination / 'SHA256.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(f'Backed up and verified {len(paths)} files: {destination}')
