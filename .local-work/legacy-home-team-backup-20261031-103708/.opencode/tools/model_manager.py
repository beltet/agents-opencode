#!/usr/bin/env python3
"""Interactive OpenCode v1 model selector for the Engineering Agent Team.

Run inside the Git project: python3 .opencode/tools/model_manager.py
Reads the actual models by running `opencode models` in the project directory.
Model overrides are stored ONLY in opencode.json -> agent.<agent>.model.
Agent Markdown files, root model, small_model, providers and auth are untouched.
This tool does not contact any endpoint itself; OpenCode may when listing models.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

MODEL_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*/[^\s]+$')
ANSI_RE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
PRIORITY = ['orchestrator', 'system-architect', 'technical-documenter', 'image-analyst']
PAGE_SIZE = 15


def stop(message):
    raise SystemExit('ERROR: ' + message)


def get_repo(value):
    repo = Path(value).expanduser().resolve()
    config = repo / 'opencode.json'
    roles = repo / '.opencode' / 'agents'
    if not repo.is_dir() or not roles.is_dir() or not config.is_file():
        stop('Run inside an installed agentteam project, or pass its path. Expected opencode.json and .opencode/agents/.')
    if config.is_symlink():
        stop('Refusing to change opencode.json through a symbolic link.')
    return repo


def load_config(repo):
    try:
        cfg = json.loads((repo / 'opencode.json').read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        stop('opencode.json is not strict JSON: ' + str(e) + '. Convert JSONC before using this tool.')
    if not isinstance(cfg, dict):
        stop('opencode.json must contain a JSON object.')
    return cfg


def all_agents(repo):
    found = [p.stem for p in (repo / '.opencode' / 'agents').glob('*.md') if p.is_file() and not p.is_symlink()]
    return [x for x in PRIORITY if x in found] + sorted(x for x in found if x not in PRIORITY)


def allowed_providers(repo, cfg):
    checks = []
    enabled = cfg.get('enabled_providers')
    if enabled is not None:
        if not isinstance(enabled, list):
            stop('enabled_providers must be a list.')
        checks.append(set(enabled))
    runtime = repo / 'PROJECT_RUNTIME_POLICY.json'
    if runtime.exists():
        if runtime.is_symlink():
            stop('Refusing runtime policy through symbolic link.')
        try:
            policy = json.loads(runtime.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            stop('Invalid PROJECT_RUNTIME_POLICY.json: '+ str(e))
        approved = policy.get('approved_providers')
        if not isinstance(approved, list):
            stop('PROJECT_RUNTIME_POLICY.json has no approved_providers array. Cannot safely assign models.')
        checks.append(set(approved))
    return set.intersection(*checks) if checks else None


def parse_model_lines(output):
    # The documented output is one `provider/model` per line; do not parse verbose metadata.
    unique = set()
    for raw in output.splitlines():
        line = ANSI_RE.sub('', raw).strip()
        if MODEL_RE.fullmatch(line):
            unique.add(line)
    return sorted(unique, key=lambda m: (m.partition('/')[0].casefold(), m.casefold()))


def get_models(repo):
    executable = shutil.which('opencode')
    if not executable:
        stop('Cannot find opencode in PATH. Install it, then run `opencode models` from the project directory.')
    try:
        process = subprocess.run([executable, 'models'], cwd=repo, text=True,
                                 capture_output=True, timeout=90, check=False)
    except subprocess.TimeoutExpired:
        stop('`opencode models` timed out (90 seconds). Try it manually; no JSON was modified.')
    if process.returncode:
        stop('`opencode models` failed. Run `opencode models` yourself in this project and check provider setup. No files changed.')
    models = parse_model_lines(process.stdout)
    if not models:
        stop('`opencode models` returned no recognizable provider/model IDs. Nothing changed. Check its output manually.')
    return models


def has_markdown_model(repo, role):
    md = repo / '.opencode' / 'agents' / (role + '.md')
    text = md.read_text(encoding='utf-8')
    if not text.startswith('---'):
        return False
    lines = text.splitlines()
    try:
        end = lines.index('---', 1)
    except ValueError:
        return False
    return any(re.match(r'^\s*model\s*:', line) for line in lines[1:end])


def effective_model(cfg, role):
    agent = cfg.get('agent', {}).get(role, {})
    if isinstance(agent, dict) and agent.get('model'):
        return agent['model']
    # A subagent without a model inherits its *calling agent*, not always root.
    return 'inherit caller'


def print_agents(repo, cfg):
    names = all_agents(repo)
    print('\nAgent models (root default: ' + str(cfg.get('model', 'not configured')) + ')')
    print('small_model: ' + str(cfg.get('small_model', 'not configured')) + ' (OpenCode internal tasks, not automatic agent routing)')
    print('An inherited subagent uses its calling agent\'s model.\n')
    for n, role in enumerate(names, 1):
        override = effective_model(cfg, role)
        marker = ' [Markdown override: edit manually]' if has_markdown_model(repo, role) else ''
        print(f'{n:2d}. {role:<27} {override}{marker}')
    return names


def save_role_model(repo, role, model):
    if role not in all_agents(repo):
        stop('Not an installed agent: ' + role)
    if has_markdown_model(repo, role):
        stop('The agent Markdown file contains model:. Remove that line first, to avoid ambiguous overrides.')
    cfg = load_config(repo)  # Reload to avoid trampling changes made since menu started.
    allowed = allowed_providers(repo, cfg)
    if model is not None:
        if not MODEL_RE.fullmatch(model):
            stop('Invalid model ID; expected exact provider/model from `opencode models`.')
        if allowed is not None and model.partition('/')[0] not in allowed:
            stop('The model provider is not approved by project policy. No changes made.')
        policyfile = repo / 'PROJECT_RUNTIME_POLICY.json'
        if policyfile.exists():
            policy = json.loads(policyfile.read_text(encoding='utf-8'))
            if policy.get('mode') == 'private':
                print('PRIVATE project: ensure the selected provider endpoint really is local. A provider ID alone does not prove it.')
    agents = cfg.setdefault('agent', {})
    if not isinstance(agents, dict):
        stop('agent must be a JSON object.')
    item = agents.get(role)
    if item is None:
        item = {}
        agents[role] = item
    if not isinstance(item, dict):
        stop('Agent configuration must be an object for ' + role)
    if model is None:
        item.pop('model', None)
        if not item:
            agents.pop(role, None)
    else:
        item['model'] = model

    path = repo / 'opencode.json'
    fd, temporary = tempfile.mkstemp(prefix='.agentteam-model-', suffix='.json', dir=repo)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(cfg, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return cfg


def select_model(role, models):
    search = ''
    page = 0
    while True:
        print(f'\nChoose model for {role} | i=inherit | b=back')
        term = input('Filter models by name/provider (Enter=all, i=inherit, b=back): ').strip()
        if term.casefold() == 'b':
            return False, None
        if term.casefold() == 'i':
            return True, None
        search = term.casefold()
        filtered = [m for m in models if search in m.casefold()]
        if not filtered:
            print('No matches. Try another filter.')
            continue
        page = 0
        while True:
            subset = filtered[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
            print(f'\nAvailable models ({len(filtered)} matched, page {page + 1}/{(len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE})')
            for i, model in enumerate(subset, 1):
                print(f' {i:2d}. {model}')
            choice = input('Model number, n=next, p=previous, f=filter, i=inherit, b=back: ').strip().lower()
            if choice == 'b':
                return False, None
            if choice == 'i':
                return True, None
            if choice == 'f':
                break
            if choice == 'n':
                if (page + 1) * PAGE_SIZE < len(filtered):
                    page += 1
                continue
            if choice == 'p':
                if page > 0:
                    page -= 1
                continue
            if choice.isdecimal() and 1 <= int(choice) <= len(subset):
                return True, subset[int(choice) - 1]
            print('Invalid choice.')


def interactive(repo, models):
    while True:
        cfg = load_config(repo)
        names = print_agents(repo, cfg)
        allowed = allowed_providers(repo, cfg)
        filtered = [m for m in models if allowed is None or m.partition('/')[0] in allowed]
        print(f'\nModels found with `opencode models`: {len(models)}; permitted by project: {len(filtered)}')
        if not filtered:
            print('No approved models available; check approved providers in project policy.')
            return
        choice = input('Agent number to change, r=reload models, q=quit: ').strip().lower()
        if choice == 'q':
            return
        if choice == 'r':
            models = get_models(repo)
            continue
        if not (choice.isdecimal() and 1 <= int(choice) <= len(names)):
            print('Invalid agent selection.')
            continue
        role = names[int(choice)-1]
        if has_markdown_model(repo, role):
            print('This role has model: in Markdown; remove that first to manage models in JSON.')
            continue
        accepted, model = select_model(role, filtered)
        if not accepted:
            continue
        if role == 'image-analyst' and model is not None:
            print('NOTE: The selected model MUST support actual image input; the model name alone is not proof.')
            if input('Have you verified image input support? [y/N]: ').strip().casefold() not in ('y', 'yes'):
                print('Not changed.')
                continue
        if model == effective_model(cfg, role):
            print('Already selected.')
            continue
        save_role_model(repo, role, model)
        print('Saved:', role, '=>', model or 'inherit caller', '| root model / small_model preserved')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', nargs='?', default='.', help='Project root (default: current directory)')
    parser.add_argument('--list', action='store_true', help='Show current assignments without fetching models')
    parser.add_argument('--models', action='store_true', help='Print models returned by opencode models, filtered by project policy')
    args = parser.parse_args()
    repo = get_repo(args.repo)
    cfg = load_config(repo)
    if args.list:
        print_agents(repo, cfg)
        return
    models = get_models(repo)
    allowed = allowed_providers(repo, cfg)
    if args.models:
        for m in models:
            if allowed is None or m.partition('/')[0] in allowed:
                print(m)
        return
    try:
        interactive(repo, models)
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled; any previous selections were saved.')


if __name__ == '__main__':
    main()
