#!/usr/bin/env python3
"""Non-security-boundary policy inspector. No network access or shell execution.
Usage: python3 .opencode/tools/access_check.py path read /path/to/file
       python3 .opencode/tools/access_check.py url https://host.example/path
"""
import argparse
import fnmatch
import json
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit


def load_policy(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    validate(data)
    return data


def absolute_policy_path(value, path_class=Path):
    """Return an absolute policy path, rejecting Windows namespace aliases.

    The default uses the host's filesystem semantics (and expands ``~``).
    PureWindowsPath may be supplied for portable lexical checks only; it does
    not resolve symlinks or make Windows paths usable on a POSIX host.
    """
    p = path_class(value)
    if isinstance(p, Path):
        p = p.expanduser()
    if isinstance(p, PureWindowsPath):
        spelling = str(p).replace('/', '\\')
        if spelling.startswith(('\\\\?\\', '\\\\.\\', '\\??\\', '\\\\??\\')):
            raise ValueError('Windows device namespaces are not supported: '+str(p))
        # Some pathlib versions classify a bare UNC server as absolute even
        # though it has no share/root and is not a usable policy directory.
        if not p.drive or not p.root:
            raise ValueError('Path must have a Windows drive/share and root: '+str(p))
    if not p.is_absolute():
        raise ValueError('Path must be absolute: '+str(p))
    return p


def is_filesystem_root(value, path_class=Path):
    """Recognize host roots, or lexical drive/share roots with PureWindowsPath.

    Native paths are resolved so aliases such as a symlink to a root cannot
    grant the whole filesystem. Pure paths only normalize dot-dot components.
    """
    p = absolute_policy_path(value, path_class)
    if isinstance(p, Path):
        p = p.resolve()
        return p == Path(p.anchor)
    parts = []
    for part in p.parts[1:]:
        if part == '..':
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return not parts


def validate(data):
    if data.get('version') != 1:
        raise ValueError('Unsupported AGENT_ACCESS_POLICY.json version')
    project = absolute_policy_path(data.get('project_root', ''))
    if is_filesystem_root(project):
        raise ValueError('Project root must not be a filesystem root')
    fs=data.get('filesystem',{})
    net=data.get('network',{})
    if not isinstance(fs.get('paths',[]),list) or not isinstance(net.get('hosts',[]),list):
        raise ValueError('Expected lists for filesystem.paths and network.hosts')
    for r in fs.get('paths',[]):
        p=absolute_policy_path(r['path'])
        if is_filesystem_root(p) and ('allow' in (r.get('read'),r.get('write'))):
            raise ValueError('Explicit root allow is not supported; use VM preset outside defaults')
        for key in ('read','write'):
            if r.get(key) not in ('allow','ask','deny'): raise ValueError('Invalid path action')
    for r in net.get('hosts',[]):
        raw=r['host']
        if not isinstance(raw,str) or not raw or '/' in raw or any(c.isspace() for c in raw):
            raise ValueError('Network rule must contain a hostname, not a full URL: '+str(raw))
        if r.get('scheme','https') not in ('https','http','ssh'): raise ValueError('Invalid scheme')
        if r.get('access') not in ('allow','ask','deny'): raise ValueError('Invalid network action')
    for d in (fs.get('default_outside',{}),):
        if any(v not in ('allow','ask','deny') for v in d.values()): raise ValueError('Invalid default path action')
    if net.get('default','deny') not in ('allow','ask','deny'): raise ValueError('Invalid network default')


def path_decision(policy, request, operation):
    if operation not in ('read','write'): raise ValueError('read or write required')
    path=Path(request).expanduser()
    # Ordinary relative requests retain their current-working-directory meaning,
    # but Windows drive-relative/rooted requests must not depend on drive state.
    if isinstance(path, PureWindowsPath) and (path.drive or path.root):
        path=absolute_policy_path(path)
    path=path.resolve()
    root=absolute_policy_path(policy['project_root']).resolve()
    if is_filesystem_root(root):
        raise ValueError('Project root must not be a filesystem root')
    try:
        path.relative_to(root)
        decision='allow'
    except ValueError:
        decision=policy.get('filesystem',{}).get('default_outside',{}).get(operation,'deny')
    # More specific directories take priority, then later rules of equal specificity.
    for rule in sorted(policy.get('filesystem',{}).get('paths',[]),key=lambda r:len(Path(r['path']).parts)):
        prefix=absolute_policy_path(rule['path']).resolve()
        if path==prefix or prefix in path.parents:
            decision=rule[operation]
    return decision


def url_decision(policy, request):
    url=urlsplit(request)
    if url.scheme not in ('https','http','ssh') or not url.hostname:
        return 'deny'
    decision=policy.get('network',{}).get('default','deny')
    for rule in policy.get('network',{}).get('hosts',[]):
        if rule.get('scheme','https')==url.scheme and fnmatch.fnmatchcase(url.hostname.lower(),rule['host'].lower()):
            if rule.get('port') is None or rule['port']==url.port:
                decision=rule['access']
    return decision


def main():
    parser=argparse.ArgumentParser(description='Advisory agent access policy check (NOT a sandbox).')
    parser.add_argument('--policy', default='AGENT_ACCESS_POLICY.json')
    sub=parser.add_subparsers(dest='kind',required=True)
    p=sub.add_parser('path'); p.add_argument('operation',choices=['read','write']); p.add_argument('target')
    u=sub.add_parser('url'); u.add_argument('target')
    a=parser.parse_args()
    policy=load_policy(a.policy)
    decision=path_decision(policy,a.target,a.operation) if a.kind=='path' else url_decision(policy,a.target)
    print(decision.upper()+' (advisory policy, NOT OS enforcement)')
    return {'allow':0,'ask':2,'deny':3}[decision]

if __name__=='__main__': raise SystemExit(main())
