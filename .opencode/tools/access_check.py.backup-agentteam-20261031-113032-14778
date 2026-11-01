#!/usr/bin/env python3
"""Non-security-boundary policy inspector. No network access or shell execution.
Usage: python3 .opencode/tools/access_check.py path read /path/to/file
       python3 .opencode/tools/access_check.py url https://host.example/path
"""
import argparse
import fnmatch
import json
from pathlib import Path
from urllib.parse import urlsplit


def load_policy(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    validate(data)
    return data


def validate(data):
    if data.get('version') != 1:
        raise ValueError('Unsupported AGENT_ACCESS_POLICY.json version')
    fs=data.get('filesystem',{})
    net=data.get('network',{})
    if not isinstance(fs.get('paths',[]),list) or not isinstance(net.get('hosts',[]),list):
        raise ValueError('Expected lists for filesystem.paths and network.hosts')
    for r in fs.get('paths',[]):
        p=Path(r['path']).expanduser()
        if not p.is_absolute(): raise ValueError('Path must be absolute: '+str(p))
        if str(p.resolve())=='/' and ('allow' in (r.get('read'),r.get('write'))):
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
    path=Path(request).expanduser().resolve()
    root=Path(policy['project_root']).expanduser().resolve()
    try:
        path.relative_to(root)
        decision='allow'
    except ValueError:
        decision=policy.get('filesystem',{}).get('default_outside',{}).get(operation,'deny')
    # More specific directories take priority, then later rules of equal specificity.
    for rule in sorted(policy.get('filesystem',{}).get('paths',[]),key=lambda r:len(Path(r['path']).parts)):
        prefix=Path(rule['path']).expanduser().resolve()
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
