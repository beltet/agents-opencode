"""Repository-only ignore rules must separate sources from local installs."""

import subprocess
import tempfile
import unittest
from pathlib import Path


class TestGitBoundary(unittest.TestCase):
    def test_local_artifacts_ignored_but_sources_visible(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / '.gitignore').write_bytes((source / '.gitignore').read_bytes())
            ignored = [
                '.opencode/agents/orchestrator.md',
                '.opencode/agent/extra.md',
                '.opencode/team/WORKFLOW.md',
                '.opencode/local/decisions.md',
                'AGENTS.md', 'PROJECT_POLICY.md', 'AGENT_ACCESS_POLICY.json',
                'opencode.json', 'opencode.jsonc',
                'AGENTS.md.backup-agentteam-20261029-120000-123',
                '.local-work/notes.md', '.local-work/decisions.md',
                '.local-work/checkpoint.md', 'session.log',
            ]
            curated = [
                '.gitignore', 'README.md', 'START_HAR.md', 'install.sh',
                'agents-opencode', 'lib/manager.py',
                'lib/profiles/orchestrator.md', 'lib/TEAM_RULES.md',
                'lib/WORKFLOW.md', 'tests/test_git_boundary.py',
                'custom-profiles/new-agent.md',
            ]
            for path, expected in [(p, 0) for p in ignored] + [(p, 1) for p in curated]:
                with self.subTest(path=path):
                    result = subprocess.run(
                        ['git', 'check-ignore', '-q', '--', path], cwd=root,
                        check=False,
                    )
                    self.assertEqual(result.returncode, expected)
