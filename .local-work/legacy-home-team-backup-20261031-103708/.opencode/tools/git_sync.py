#!/usr/bin/env python3
"""Guarded ordinary Git remote actions for one approved repository/remote.

Usage (from project root):
  python3 .opencode/tools/git_sync.py status
  python3 .opencode/tools/git_sync.py fetch
  python3 .opencode/tools/git_sync.py pull
  python3 .opencode/tools/git_sync.py push

Requires PROJECT_RUNTIME_POLICY.json installed by install.py. Never force pushes,
never deletes refs, never changes remote or credentials.
"""
import json
import os
from pathlib import Path
import subprocess
import sys


def die(message):
    print('DENIED:', message, file=sys.stderr)
    raise SystemExit(2)


def git(*args, capture=False):
    kw = dict(cwd=Path.cwd(), check=True, text=True)
    if capture:
        kw.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return subprocess.run(['git', '--no-pager', *args], **kw)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {'status', 'fetch', 'pull', 'push'}:
        die('Usage: git_sync.py status|fetch|pull|push (no extra arguments)')
    action = sys.argv[1]
    root = Path.cwd().resolve()
    try:
        repo = Path(git('rev-parse', '--show-toplevel', capture=True).stdout.strip()).resolve()
    except (subprocess.CalledProcessError, ValueError):
        die('Current directory is not a Git repository')
    if root != repo:
        die('Run only from the exact project repository root')
    config = repo / 'PROJECT_RUNTIME_POLICY.json'
    if config.is_symlink() or not config.is_file():
        die('No regular PROJECT_RUNTIME_POLICY.json')
    settings = json.loads(config.read_text(encoding='utf-8'))
    if Path(settings.get('repo_root', '')).resolve() != repo:
        die('Configured workspace differs from active Git root')
    if action == 'status':
        git('status', '--short', '--branch')
        return
    remote = settings.get('git_remote', {})
    name, approved_url = remote.get('name'), remote.get('url')
    if not name or not approved_url:
        die('No approved Git remote: configure one explicitly with install.py')
    if action not in remote.get('allow', []):
        die(f'Remote operation {action} was not approved at installation')
    try:
        actual = git('remote', 'get-url', name, capture=True).stdout.strip()
    except subprocess.CalledProcessError:
        die('Approved remote name does not exist')
    if actual != approved_url:
        die('Actual remote URL does not exactly match the approved URL')
    if action == 'fetch':
        git('fetch', '--no-tags', name)
        return
    branch = git('symbolic-ref', '--quiet', '--short', 'HEAD', capture=True).stdout.strip()
    if not branch or branch.startswith('-') or ':' in branch or branch.startswith('refs/'):
        die('Unsafe/unnamed branch')
    protected = remote.get('protected_branches', ['main', 'master'])
    if branch in protected and not remote.get('allow_protected_branch', False):
        die('Protected branch requires manual approval')
    if action == 'pull':
        git('pull', '--ff-only', '--no-rebase', name, branch)
    if action == 'push':
        git('push', '--porcelain', name, f'refs/heads/{branch}:refs/heads/{branch}')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as e:
        die(f'Git command failed: {e}')
