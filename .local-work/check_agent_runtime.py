"""Local-only load check; does not invoke a model or alter the working project."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import manager

permissions = dict(shell='allow', file_edit='allow', gitpush='deny', internet='deny',
                   outside_read='deny', outside_write='deny', sudo='deny',
                   destructive='deny', secrets='deny', mcp='deny', packages='deny',
                   hardware='deny', unattended=False, mounts=[])
with tempfile.TemporaryDirectory(prefix='agent-runtime-') as directory:
    project = Path(directory)
    roles = list(manager.profiles())
    manager.apply(project, roles, {name: None for name in roles}, permissions, 'SHAREABLE')
    # Isolate the user's global agents/config: inherited fields (including steps)
    # can survive when project profiles omit those fields.
    env = {**os.environ, 'HOME': str(project),
           'XDG_CONFIG_HOME': str(project / 'config'),
           'XDG_DATA_HOME': str(project / 'data'),
           'XDG_STATE_HOME': str(project / 'state'),
           'XDG_CACHE_HOME': str(project / 'cache'),
           'OPENCODE_DISABLE_DEFAULT_PLUGINS': '1', 'OPENCODE_PURE': '1'}
    env.pop('OPENCODE_CONFIG', None)
    env.pop('OPENCODE_CONFIG_DIR', None)
    if '--real-home' in sys.argv:
        env = dict(os.environ)
    for name in roles:
        result = subprocess.run(['opencode', 'debug', 'agent', name], cwd=project,
                                env=env, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(f'{name}: {result.stderr}\n{result.stdout}')
        loaded = json.loads(result.stdout)
        assert not loaded.get('steps'), (name, loaded.get('steps'))
        assert not loaded.get('maxSteps'), (name, loaded.get('maxSteps'))
        assert loaded['mode'] == ('primary' if name == 'orchestrator' else 'subagent')
        assert 'WORKFLOW.md' in loaded['prompt'], name
        print(f'Loaded {name}: mode={loaded["mode"]}, no step cap')
    print(f'OpenCode runtime check: {len(roles)} profiles passed; no model invoked.')
