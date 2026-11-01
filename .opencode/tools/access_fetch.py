#!/usr/bin/env python3
"""Read-only, policy-checked HTTP GET helper. NOT a security boundary.

No automatic redirects. No credentials or POST. Response capped at 2 MiB.
The containing shell remains capable of bypassing this helper.
"""
import argparse
import sys
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from access_check import load_policy, url_decision

MAX_BYTES=2*1024*1024

class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def main():
    p=argparse.ArgumentParser(description='Policy-checked fetch; advisory only, not a sandbox')
    p.add_argument('url',help='Explicit URL, without authentication tokens')
    p.add_argument('--policy',default='AGENT_ACCESS_POLICY.json')
    a=p.parse_args()
    policy=load_policy(a.policy)
    if not a.url.startswith(('https://','http://')) or url_decision(policy,a.url)!='allow':
        print('DENIED by AGENT_ACCESS_POLICY.json',file=sys.stderr)
        return 3
    try:
        req=Request(a.url,headers={'User-Agent':'agents-opencode-access-fetch/2.1','Accept':'text/plain,text/html,application/json,*/*;q=0.2'})
        # Redirects intentionally disabled. If a new destination is needed, approve it separately.
        with build_opener(NoRedirects).open(req, timeout=12) as response:
            data=response.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES:
                print('Response too large (>2 MiB); refused',file=sys.stderr)
                return 4
            ctype=response.headers.get_content_charset() or 'utf-8'
            print(data.decode(ctype,errors='replace'))
        return 0
    except (HTTPError,URLError,TimeoutError) as ex:
        print('Fetch failed (redirects are not followed): '+str(ex),file=sys.stderr)
        return 5

if __name__=='__main__':raise SystemExit(main())
