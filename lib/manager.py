#!/usr/bin/env python3
"""OpenCode v1.x portable user-level agent team installer. Python stdlib only.
The user-facing command is the `agents-opencode` Bash script.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from access_check import load_policy, validate, path_decision, url_decision

VERSION = '2.1.0'
ROOT = Path(__file__).resolve().parent
PROFILES = ROOT / 'profiles'
CUSTOM = ROOT.parent / 'custom-profiles'
MANIFEST = Path('.opencode/agentteam-manifest.json')
ACCESS_FILE = 'AGENT_ACCESS_POLICY.json'
ACCESS_RULES = '.opencode/team/ACCESS_RULES.md'
MARK_OPEN = '<!-- agents-opencode managed section START -->'
MARK_CLOSE = '<!-- agents-opencode managed section END -->'
ACTIONS = {'a':'allow','q':'ask','d':'deny'}


def say(msg=''): print(msg, flush=True)
def prompt(msg, default=''):
    value = input(f'{msg}' + (f' [{default}]' if default else '') + ': ').strip()
    return value if value else default

def confirm(msg, default=False):
    hint = 'J/n' if default else 'j/N'
    while True:
        ans = input(f'{msg} [{hint}]: ').strip().lower()
        if not ans: return default
        if ans in ('j','ja','y','yes'): return True
        if ans in ('n','nej','no'): return False
        say('Svara j eller n.')

def choose(msg, options, default=''):
    for k, desc in options: say(f'  {k}) {desc}')
    accepted = {k for k,_ in options}
    while True:
        ans=prompt(msg,default)
        if ans in accepted: return ans
        say('Ogiltigt val.')

def policy_action(title, default):
    d = {'allow':'a','ask':'q','deny':'d'}[default]
    return ACTIONS[choose(title, [('a','Tillåt utan fråga'),('q','Fråga varje gång'),('d','Neka')],d)]

def project_dir(arg=None):
    if arg: return Path(arg).expanduser().resolve()
    return Path(prompt('Projektkatalog',str(Path.cwd()))).expanduser().resolve()

def profiles():
    out = {p.stem:p for p in PROFILES.glob('*.md')}
    CUSTOM.mkdir(parents=True,exist_ok=True)
    for p in CUSTOM.glob('*.md'): out[p.stem] = p
    return dict(sorted(out.items()))

def titles(filename):
    t=filename.read_text(encoding='utf-8').split('---',2)
    if len(t)<3: return filename.stem
    m=re.search(r'^description:\s*(.+)$', t[1], re.M)
    return (m.group(1).strip(' "\'') if m else filename.stem)[:76]

def select_agents(available, old=None):
    ids=list(available)
    say('\n=== Välj vilka agenter som ska installeras ===')
    for i,name in enumerate(ids,1):
        tick = '*' if (old and name in old) else ' '
        say(f'{i:>2}) [{tick}] {name:26} {titles(available[name])}')
    say('\nAnge a = alla, c = kärnteamet, siffror (ex. 1,3,6-9) eller Enter för tidigare val.')
    while True:
        answer=prompt('Agenter', 'föregående' if old else 'c')
        if answer=='a': selected=ids
        elif answer=='c': selected=[x for x in ('orchestrator','system-architect','technical-documenter') if x in available]
        elif answer=='föregående' and old: selected=[x for x in ids if x in old]
        else:
            try:
                ix=set()
                for part in answer.replace(' ','').split(','):
                    if '-' in part:
                        x,y=map(int,part.split('-',1)); ix.update(range(x,y+1))
                    else: ix.add(int(part))
                if not ix or any(n<1 or n>len(ids) for n in ix): raise ValueError()
                selected=[ids[n-1] for n in sorted(ix)]
            except Exception:
                say('Ogiltig lista. Exempel: a, c, 1,3,6-9'); continue
        if selected:
            say(f'Valt {len(selected)}: '+', '.join(selected))
            if 'orchestrator' not in selected:
                say('OBS: Orkestreraren saknas. Du måste själv leda teamet eller välja en annan huvudagent.')
            if confirm('Använd detta urval?',True): return selected
        else: say('Välj minst en agent.')

def list_models(cwd):
    # Test hook: no runtime dependency on mock data. Real installations call OpenCode.
    fixture=os.getenv('AGENTS_OPENCODE_TEST_MODELS_FILE')
    if fixture:
        text=Path(fixture).read_text()
    else:
        if not shutil.which('opencode'):
            raise RuntimeError('opencode saknas i PATH; installera/autentisera OpenCode först.')
        say('\nHämtar modellistan med: opencode models')
        r=subprocess.run(['opencode','models'],cwd=cwd,capture_output=True,text=True,timeout=90)
        if r.returncode: raise RuntimeError('opencode models misslyckades:\n'+r.stderr[-1000:])
        text=r.stdout
    result=[]
    for line in text.splitlines():
        value=line.strip()
        if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_./:@-]*',value):
            if value not in result: result.append(value)
    if not result: raise RuntimeError('Inga modell-ID hittades i opencode models.')
    return result

def pick_model(name, catalog, old=None, previous=None):
    say(f'\n=== Modell för {name} ===')
    say(f'Nuvarande: {old or "ingen vald"}. Alla {len(catalog)} modeller visas:')
    for i,m in enumerate(catalog,1): say(f'{i:>3}) {m}')
    hints=[]
    if old: hints.append('Enter = behåll')
    if previous: hints.append('p = använd föregående val')
    hints.append('i = ärv från anropande agent')
    say(' | '.join(hints))
    while True:
        v=prompt('Modellnummer')
        if not v and old: return old
        if v.lower()=='i': return None
        if v.lower()=='p' and previous: return previous
        if v.isdigit() and 1<=int(v)<=len(catalog):
            m=catalog[int(v)-1]
            if name=='image-analyst': say('OBS: kontrollera att modellen verkligen har stöd för bildinmatning.')
            return m
        say('Ange ett nummer från listan'+(', p, i eller Enter' if old else ', p eller i')+'.')

def assign_models(selected, catalog, existing=None):
    results={}; last=None
    for name in selected:
        old=(existing or {}).get(name)
        model=pick_model(name,catalog,old,last)
        results[name]=model
        if model: last=model
    return results

def json_load(path):
    if not path.exists(): return {}
    try:
        v=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(v,dict): raise ValueError('Root must be an object')
        return v
    except (ValueError,UnicodeError) as ex:
        raise RuntimeError(f'{path} kunde inte läsas som vanlig JSON. Gör om JSONC till JSON innan ändring: {ex}')

def backup(path):
    if path.exists():
        name=path.with_name(path.name+'.backup-agentteam-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
        shutil.copy2(path,name)
        return name
    return None

def write_text(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_text(encoding='utf-8')==text: return
    backup(path)
    tmp=path.with_name('.'+path.name+'.tmp-'+str(os.getpid()))
    tmp.write_text(text,encoding='utf-8')
    os.replace(tmp,path)

def write_json(path,config): write_text(path,json.dumps(config,ensure_ascii=False,indent=2)+'\n')

def read_manifest(project):
    try: return json_load(project/MANIFEST)
    except Exception: return {}

def choose_mode():
    say('\n=== Projektets informationsklassning ===')
    k=choose('Välj klassning',[('1','PRIVATE: endast godkända lokala modellanslutningar'),('2','SHAREABLE: godkända molnmodeller, projektets tillåtna data'),('3','HYBRID: lokal + moln; sekretess måste hanteras separat')],'1')
    mode={'1':'PRIVATE','2':'SHAREABLE','3':'HYBRID'}[k]
    if mode=='PRIVATE':
        say('KRITISKT: verktyget kan inte avgöra om en provider faktiskt vidarebefordrar data till molnet.')
        if not confirm('Bekräftar du att ALLA valda modeller verkligen är lokalt hostade och att projektet får skickas till dessa endpoints?',False):
            raise RuntimeError('PRIVATE kräver verifierad lokal modellanslutning. Avbrutet.')
    else:
        if not confirm('Får godkända molnmodeller behandla den delbara källkod och kontext som ligger i projektet?',False):
            raise RuntimeError('Molnbehandling inte godkänd. Avbrutet.')
    return mode

def ask_mounts():
    mounts=[]
    say('Ange absoluta katalogsökvägar för tillåtna nätverksdiskar. Tom rad avslutar.')
    while True:
        val=prompt('Monterad katalog (eller Enter)')
        if not val: break
        p=Path(val).expanduser().resolve()
        if not p.is_dir() or not p.is_absolute(): say('Katalogen måste finnas som en absolut sökväg.'); continue
        r=policy_action(f'Läsa {p}', 'allow')
        w=policy_action(f'Skriva {p}', 'deny')
        mounts.append({'path':str(p),'read':r,'write':w})
    return mounts

def permission_wizard(existing=None):
    say('\n=== Behörighetsguide ===')
    presets={
      '1':dict(shell='ask',file_edit='ask',gitpush='deny',internet='deny',outside_read='deny',outside_write='deny',sudo='deny',destructive='deny',secrets='deny',mcp='deny',packages='deny',hardware='deny',unattended=False),
      '2':dict(shell='allow',file_edit='allow',gitpush='ask',internet='ask',outside_read='deny',outside_write='deny',sudo='deny',destructive='ask',secrets='deny',mcp='ask',packages='ask',hardware='deny',unattended=False),
      '3':dict(shell='allow',file_edit='allow',gitpush='allow',internet='allow',outside_read='allow',outside_write='allow',sudo='allow',destructive='allow',secrets='ask',mcp='allow',packages='allow',hardware='ask',unattended=True)
    }
    say('Förinställningar ändrar bara behörigheter, ALDRIG modellval.')
    n=choose('Startläge',[('1','Låst arbetsdator'),('2','Utvecklingsdator'),('3','Isolerad VM med stora rättigheter'),('4','Utgå från projektets nuvarande behörigheter')], '4' if existing else '2')
    base=dict(existing) if n=='4' and existing else dict(presets.get(n,presets['2']))
    say('\nJustera vart och ett av valen (a=allow, q=ask, d=deny):')
    # Repair older v2 manifests that do not contain newly introduced controls.
    for k,default in [('file_edit','allow'),('mcp','ask'),('packages','ask'),('hardware','deny')]: base.setdefault(k,default)
    base['shell']=policy_action('Shellkommandon generellt',base['shell'])
    base['file_edit']=policy_action('Skriva/redigera projektfiler genom OpenCodes filverktyg',base['file_edit'])
    base['gitpush']=policy_action('Git push mot remote',base['gitpush'])
    base['internet']=policy_action('Internet via OpenCode webfetch/websearch + direkt curl/wget/ssh i shell',base['internet'])
    base['outside_read']=policy_action('Läsa utanför projektmappen med OpenCodes filverktyg',base['outside_read'])
    base['outside_write']=policy_action('Skriva utanför projektmappen med OpenCodes filverktyg',base['outside_write'])
    base['sudo']=policy_action('Sudo och privilegierade kommandon',base['sudo'])
    base['destructive']=policy_action('Potentiellt destruktiva shellkommandon',base['destructive'])
    base['secrets']=policy_action('Läsa hemligheter/nyckelfiler med filverktyg',base['secrets'])
    base['mcp']=policy_action('Anropa externa MCP-verktyg och anslutna externa tjänster',base['mcp'])
    base['packages']=policy_action('Installera system- eller språkpaket via vanliga kommandomönster',base['packages'])
    base['hardware']=policy_action('Firmwareflashning och verktyg för hårdvarusändning (best effort)',base['hardware'])
    base['mounts']=ask_mounts() if confirm('Konfigurera specifika nätverksdiskar nu?',bool(base.get('mounts'))) else base.get('mounts',[])
    say('\nObevakad körning med --auto godkänner även regler som annars skulle fråga.')
    base['unattended']=confirm('Aktivera obevakat läge för detta projekt?',bool(base.get('unattended')))
    if base['shell']=='allow':
        say('VARNING: shell=allow är lika med värdanvändarens åtkomst. Python, byggskript och Git-hooks kan kringgå mönsterregler för filer/nätverk.')
    if base['unattended'] and any(base[k]=='ask' for k in ('gitpush','internet','outside_read','outside_write','sudo','destructive','secrets','packages','hardware','mcp')):
        say('VARNING: --auto godkänner ASK. Ändra till DENY om en åtgärd verkligen ska förbli blockerad obevakat.')
    if base['shell']=='allow' and base['outside_read']=='deny':
        say('VARNING: utanför-projekt=deny skyddar inte mot shellkommandon med rättigheter på värdsystemet.')
    if not confirm('Bekräfta denna behörighetsprofil?',False): raise RuntimeError('Behörighetskonfiguration avbruten')
    return base



def default_access_policy(project, perm):
    """Project-root implicit allow, everything outside explicitly denied by default.
    Explicitly permissive VM presets are represented by their chosen defaults.
    """
    fs_rules=[]
    for m in perm.get('mounts',[]):
        fs_rules.append({'path':m['path'],'kind':'network-share','read':m['read'],'write':m['write']})
    return {
        'version':1, 'advisory_only':True, 'project_root':str(project),
        'filesystem':{'default_outside':{'read':perm.get('outside_read','deny'),'write':perm.get('outside_write','deny')},'paths':fs_rules},
        'network':{'default':perm.get('internet','deny'),'hosts':[]},
        'model_api_note':'Configured AI model provider traffic is controlled separately; this list is for agent-initiated network requests.',
        'warning':'NOT A SANDBOX: OpenCode tool rules and agent instructions cannot prevent arbitrary shell subprocesses, symlink or network escapes.'
    }


def render_access_rules(access):
    """English instructions injected as an OpenCode instructions file."""
    fs=access['filesystem']; net=access['network']
    lines=['# Agent access rules (project-specific, mandatory instructions)', '',
       '**WARNING: ADVISORY, NOT ACTUAL SECURITY.** These rules describe authorized behavior, not an operating-system sandbox.',
       'A permitted shell command, program, symlink, Git hook or plugin can bypass these rules. Never interpret this document as technical isolation.',
       'Before accessing resources, consult `AGENT_ACCESS_POLICY.json`. When unsure, use `python3 .opencode/tools/access_check.py path read /absolute/path`,',
       '`python3 .opencode/tools/access_check.py path write /absolute/path`, or `python3 .opencode/tools/access_check.py url https://host/path`.',
       'These checks are advisory and do not perform the operation. Deny means stop; ask means request user authorization (do not treat --auto as approval to expand the policy).',
       'For explicitly allowed public HTTP(S) sites, `python3 .opencode/tools/access_fetch.py https://allowed-host/path` can retrieve up to 2 MiB (GET only; no redirects).',
       'Never rewrite the policy or this document as a workaround. Request changes from the owner through agents-opencode.',
       '', '## Filesystem',
       '- The project directory is permitted for normal project work. The filesystem root `/` and all other locations are **denied by default** unless explicitly allowed below.',
       '- Resolved paths (including symlinks) count; a mount can be read-only independently of local paths.',
       f"- Outside defaults: read={fs['default_outside']['read'].upper()}, write={fs['default_outside']['write'].upper()}." ]
    if fs['default_outside']['read']!='deny' or fs['default_outside']['write']!='deny':
        lines.append('- BROAD ACCESS EXCEPTION: the owner explicitly selected permissive defaults (e.g. VM mode). This is a deliberate override of root-deny behavior.')
    for r in fs.get('paths',[]):
        lines.append(f"- {r['path']} ({r.get('kind','local')}): read={r['read'].upper()}, write={r['write'].upper()}.")
    lines+=['', '## Network requests by agents',
       f"- Default: {net['default'].upper()}; HTTPS/HTTP/SSH host rules below are decisions about agent-initiated requests, not model-provider calls.",
       '- Apply host patterns to the resolved destination, including redirects; do not use redirects or alternate IPs to bypass restrictions.',
       '- OpenCode 1.x webfetch cannot restrict individual URLs, so generated OpenCode permissions will disable unrestricted webfetch when an allowlist exists.',
       '- Any allowed network request is only an authorization statement; the actual tool/OS must also permit it.',
       '- Authorized Git remote access is separately defined by project Git policy. A Git remote does not imply permission to browse or contact other hosts.']
    for r in net.get('hosts',[]):
        lines.append(f"- {r.get('scheme','https')}://{r['host']}{(':'+str(r['port'])) if r.get('port') else ''}: {r['access'].upper()}.")
    lines+=['', '## Cloud model data',
       '- This agent-initiated network policy does not inspect or filter data sent to a configured cloud model. Respect PRIVATE/HYBRID rules independently.',
       '- Agents must report a blocked requirement and ask the orchestrator for owner approval, not route around the policy.', '']
    return '\n'.join(lines)


def access_wizard(project, access):
    """Edit one shared declarative policy. A sorted path rule can override broader rules."""
    access=json.loads(json.dumps(access))
    say('\n=== Åtkomstpolicy: whitelist / blacklist (INTE en säker sandbox) ===')
    say('Projektmappen tillåts. Root / och övriga kataloger nekas som standard.')
    fs=access['filesystem']; net=access['network']
    if confirm('Ändra standardåtkomst utanför projektet?',False):
        fs['default_outside']['read']=policy_action('Standard: läsa utanför projektet',fs['default_outside']['read'])
        fs['default_outside']['write']=policy_action('Standard: skriva utanför projektet',fs['default_outside']['write'])
    if confirm('Ange tillåtna/blockerade lokala kataloger eller nätverksdiskar?',False):
        say('Ange absolut sökväg. Varje katalogregel omfattar även underkataloger. Tomt avslutar.')
        while True:
            value=prompt('Sökväg')
            if not value: break
            path=str(Path(value).expanduser().resolve())
            if path=='/':
                say('En explicit allow för / stöds inte. Välj bred VM-standard om den nivån av åtkomst behövs.'); continue
            kind=choose('Typ',[('1','Lokal sökväg'),('2','Monterad nätverksdisk')],'1')
            r=policy_action('Läsa', 'allow'); w=policy_action('Skriva','deny')
            fs['paths']=[x for x in fs['paths'] if x['path']!=path]
            fs['paths'].append({'path':path,'kind':'network-share' if kind=='2' else 'local','read':r,'write':w})
        if fs['paths'] and confirm('Ta bort någon befintlig katalogregel?',False):
            for i,x in enumerate(fs['paths'],1): say(f'{i}) {x["path"]} ({x["read"]}/{x["write"]})')
            number=prompt('Nummer (Enter=ingen)')
            if number.isdigit() and 1<=int(number)<=len(fs['paths']):fs['paths'].pop(int(number)-1)
    if confirm('Ändra standardåtkomst för agenters internetanrop?',False):
        net['default']=policy_action('Standard: internet',net['default'])
    if confirm('Ange tillåtna/blockerade internetvärdar?',False):
        say('Ange värdnamn, t.ex. docs.python.org eller *.example.org. Tomt avslutar.')
        while True:
            host=prompt('Värdnamn')
            if not host: break
            if '/' in host or any(c.isspace() for c in host):
                say('Endast värdnamn, inte hel URL.'); continue
            scheme=choose('Protokoll',[('1','https'),('2','http'),('3','ssh')],'1')
            port=prompt('Port, Enter = standard')
            if port and (not port.isdigit() or not 1<=int(port)<=65535):say('Ogiltig port'); continue
            action=policy_action('Åtkomst', 'allow')
            entry={'host':host.lower(),'scheme':{'1':'https','2':'http','3':'ssh'}[scheme],'access':action}
            if port:entry['port']=int(port)
            net['hosts']=[r for r in net['hosts'] if (r['host'],r.get('scheme'),r.get('port'))!=(entry['host'],entry['scheme'],entry.get('port'))]
            net['hosts'].append(entry)
        if net['hosts'] and confirm('Ta bort någon befintlig värdregel?',False):
            for i,x in enumerate(net['hosts'],1):say(f'{i}) {x.get("scheme","https")}://{x["host"]} {x["access"]}')
            number=prompt('Nummer (Enter=ingen)')
            if number.isdigit() and 1<=int(number)<=len(net['hosts']):net['hosts'].pop(int(number)-1)
    validate(access)
    say('OBS: denna fil är en beteendepolicy; utan OS-sandbox kan shellkommandon kringgå den.')
    if not confirm('Spara dessa åtkomstregler?',False): raise RuntimeError('Åtkomstguiden avbruten')
    return access

def make_permission(v, access=None):
    # V1 OpenCode has `permission` singular; last matching pattern wins.
    shell={'*':v['shell']}
    for p in ['git push*','git -C * push*']:
        shell[p]=v['gitpush']
    # These globs are advisory, not OS confinement or network address ACLs.
    for p in ['curl *','wget *','ssh *','scp *','rsync *','git clone *','git fetch *','git pull *']:
        shell[p]=v['internet']
    for p in ['sudo *','su *','pkexec *']:
        shell[p]=v['sudo']
    for p in ['rm *','dd *','mkfs*','wipefs *','shred *','git reset --hard*','git clean -fd*']:
        shell[p]=v['destructive']
    # Force-push may never be less restrictive than either Git push or destructive policy.
    rank={'deny':0,'ask':1,'allow':2}
    force_mode=min((v['destructive'],v['gitpush']),key=lambda x:rank[x])
    for p in ['git push --force*','git push -f *','git -C * push --force*','git -C * push -f *']:
        shell[p]=force_mode
    for p in ['dnf *','yum *','apt *','apt-get *','pacman *','pip install *','pip3 install *','python -m pip install *','python3 -m pip install *','cargo install *','npm install -g *']:
        shell[p]=v.get('packages','ask')
    for p in ['flashrom *','dfu-util *','openocd *','uhd_image_loader *','hackrf_transfer *']:
        shell[p]=v.get('hardware','deny')
    read={'*':'allow'}
    edit={'*':v.get('file_edit','allow')}
    ext={'*': 'allow' if 'allow' in (v['outside_read'],v['outside_write']) else ('ask' if 'ask' in (v['outside_read'],v['outside_write']) else 'deny')}
    # Read/edit absolute path match complements external_directory.
    read['/*']=v['outside_read']; edit['/*']=v['outside_write']
    for m in v.get('mounts',[]):
        path=m['path'].rstrip('/')
        ext[path+'/*']='allow' if 'allow' in (m['read'],m['write']) else ('ask' if 'ask' in (m['read'],m['write']) else 'deny')
        read[path+'/*']=m['read']; edit[path+'/*']=m['write']
    if access:
        # Native OpenCode v1.x external-directory and read/edit guards are best effort.
        fs=access['filesystem']; net=access['network']
        ext['*']='allow' if 'allow' in fs['default_outside'].values() else ('ask' if 'ask' in fs['default_outside'].values() else 'deny')
        read['/*']=fs['default_outside']['read']
        edit['/*']=fs['default_outside']['write']
        # Explicit project-root exception avoids rejecting absolute paths within the worktree.
        root=access['project_root'].rstrip('/')
        for pat in (root, root+'/**'):
            read[pat]='allow'
            edit[pat]=v.get('file_edit','allow')
        for r in sorted(fs.get('paths',[]),key=lambda x:len(Path(x['path']).parts)):
            path=r['path'].rstrip('/')
            for pat in (path, path+'/**'):
                ext[pat]='allow' if 'allow' in (r['read'],r['write']) else ('ask' if 'ask' in (r['read'],r['write']) else 'deny')
                read[pat]=r['read']; edit[pat]=r['write']
        # OpenCode v1.x cannot implement webfetch host allowlists. Avoid unintentionally broad allow.
        network_safe=net['default'] if not net.get('hosts') else 'deny'
        v={**v,'_webfetch_permission':network_safe}
    # Never let the agent rewrite its own access policy via direct edit tools.
    if access and any(r['access']=='allow' and r.get('scheme','https') in ('https','http') for r in access['network'].get('hosts',[])):
        shell['python3 .opencode/tools/access_fetch.py *']='allow'
    for pat in (ACCESS_FILE, ACCESS_RULES, '.opencode/tools/access_check.py', '.opencode/tools/access_fetch.py'):
        edit[pat]='deny'
        if access:
            edit[str(Path(access['project_root'])/pat)]='deny'
    # Secrets patterns after generic catchalls. Some paths/aliases may evade these globs.
    for pat in ['*.env','*.env.*','*.pem','*.key','*id_rsa*','*id_ed25519*','*credentials*','*secrets*']:
        read[pat]=v['secrets']; edit[pat]='deny' if v['secrets']!='allow' else 'ask'
    read['*.env.example']='allow'
    task={'*':'deny'}
    for name in v.get('_selected_agents',[]): task[name]='allow'
    return {'bash':shell,'read':read,'edit':edit,'external_directory':ext,
            'webfetch':v.get('_webfetch_permission',v['internet']),'websearch':'deny' if (access and access['network'].get('hosts')) else v['internet'], 'doom_loop':'deny' if v['unattended'] else 'ask',
            'task':task, 'mcp_*':v.get('mcp','ask')}

def managed_section(selected, mode):
    summary=', '.join(selected)
    return (MARK_OPEN+'\n'
       '## Installed OpenCode engineering team (managed)\n'
       f'Installed specialists ({len(selected)}): {summary}.\n\n'
       'Only activate a specialist when its expertise is required. If present, orchestrator coordinates; '
       'system-architect and technical-documenter join the core when installed. '\
       'Follow `.opencode/team/TEAM_RULES.md`, `.opencode/team/WORKFLOW.md`, `PROJECT_POLICY.md` and `AGENT_ACCESS_POLICY.json`.\n'
       'Admit uncertainty; verify small experiments before costly simulations; hand off concise findings.\n'
       f'Project classification: **{mode}**. A selected cloud model may see project context; never send secrets.\n'
       'Technical agent profiles are written in English; communicate in the user’s requested language.\n'
       +MARK_CLOSE)

def update_agents_md(project, selected, mode):
    file=project/'AGENTS.md'; text=file.read_text(encoding='utf-8') if file.exists() else ''
    new=managed_section(selected,mode)
    old_template=(ROOT/'LEGACY_AGENTS.md').read_text(encoding='utf-8')
    if MARK_OPEN in text and MARK_CLOSE in text:
        a=text.index(MARK_OPEN); b=text.index(MARK_CLOSE,a)+len(MARK_CLOSE)
        text=text[:a]+new+text[b:]
    elif old_template.strip() in text:
        text=text.replace(old_template.strip(),new,1)
    else:
        if '# Project AI team instructions' in text:
            say('VARNING: AGENTS.md har äldre agentteam-regler som inte kunde identifieras exakt. Kontrollera konflikter manuellt.')
        text=text.rstrip()+'\n\n'+new+'\n'
    write_text(file,text)

def apply(project, selected, models, perm, mode, approved_remote=None, access=None):
    if not project.is_dir(): raise RuntimeError('Projektkatalogen finns inte')
    existing=json_load(project/'opencode.json')
    if access is None:
        access=load_policy(project/ACCESS_FILE) if (project/ACCESS_FILE).exists() else default_access_policy(project,perm)
    validate(access)
    if Path(access['project_root']).resolve()!=project.resolve():
        raise RuntimeError('Åtkomstpolicyn tillhör ett annat projekt; ändra project_root efter flytt.')
    manifest=read_manifest(project)
    old_managed=set(manifest.get('installed_agents',[]))
    known=set(profiles())
    agents_dir=project/'.opencode/agents'; agents_dir.mkdir(parents=True,exist_ok=True)
    # When upgrading v1.x without a manifest, only remove known packaged roles if explicitly deselected.
    if not old_managed:
        old_managed={p.stem for p in agents_dir.glob('*.md') if p.stem in known}
    for name in old_managed-set(selected):
        target=agents_dir/(name+'.md')
        if target.exists():
            backup(target); target.unlink()
    for name in selected:
        template=profiles()[name]
        write_text(agents_dir/(name+'.md'),template.read_text(encoding='utf-8'))
    cfg=existing
    cfg.setdefault('$schema','https://opencode.ai/config.json')
    a=cfg.get('agent') or {}
    if not isinstance(a,dict): raise RuntimeError('opencode.json agent måste vara ett objekt')
    for name in old_managed-set(selected):
        a.pop(name,None)
    for name in selected:
        value=dict(a.get(name) or {})
        if models.get(name): value['model']=models[name]
        else: value.pop('model',None)
        # Clear previous agent-specific permission overrides from old packages;
        # the configured project profile is authoritative for these managed agents.
        value.pop('permission',None)
        a[name]=value
    cfg['agent']=a
    if 'orchestrator' in selected:
        cfg['default_agent']='orchestrator'
        if models.get('orchestrator'): cfg['model']=models['orchestrator']
    else:
        if cfg.get('default_agent')=='orchestrator':
            cfg.pop('default_agent',None)
        if selected and not cfg.get('model'):
            first=next((models.get(n) for n in selected if models.get(n)),None)
            if first: cfg['model']=first
    cfg['permission']=make_permission({**perm,'_selected_agents':selected},access)
    instructions=cfg.get('instructions',[])
    if not isinstance(instructions,list):raise RuntimeError('opencode.json instructions måste vara en lista')
    if ACCESS_RULES not in instructions:instructions.append(ACCESS_RULES)
    cfg['instructions']=instructions
    provider_ids=sorted({m.split('/')[0] for m in models.values() if m})
    if provider_ids:
        cfg['enabled_providers']=provider_ids
    write_json(project/'opencode.json',cfg)
    team=project/'.opencode/team'
    team.mkdir(parents=True,exist_ok=True)
    for t in ['TEAM_RULES.md','WORKFLOW.md','HANDOFF_TEMPLATE.md']:
        content=(ROOT/t).read_text(encoding='utf-8')
        # change outdated count for selected subset (no 23-role claims)
        content=content.replace('all 23 agents','the installed agents').replace('all 23','all installed').replace('23 agents','available agents').replace('remaining 20 experts','other selected experts')
        write_text(team/t,content)
    write_json(project/ACCESS_FILE,access)
    write_text(project/ACCESS_RULES,render_access_rules(access))
    (project/'.opencode/tools').mkdir(parents=True,exist_ok=True)
    write_text(project/'.opencode/tools/access_check.py',(ROOT/'access_check.py').read_text(encoding='utf-8'))
    write_text(project/'.opencode/tools/access_fetch.py',(ROOT/'access_fetch.py').read_text(encoding='utf-8'))
    update_agents_md(project,selected,mode)
    remote=approved_remote if approved_remote is not None else manifest.get('approved_remote')
    info={'version':VERSION,'installed_agents':selected,'models':models,'mode':mode,
          'permissions':perm,'access_policy':ACCESS_FILE,'approved_remote':remote,'models_source':'opencode models'}
    write_json(project/MANIFEST,info)
    policy=(f'# Project policy (generated by agents-opencode {VERSION})\n\n'
       f'- Data classification: **{mode}**.\n'
       '- Project root: '+str(project)+'\n'
       '- Selected agents: '+', '.join(selected)+'\n'
       '- Models: explicit choices saved in `opencode.json`; no defaults are built into the installer.\n'
       '- Model APIs: only approved providers, subject to actual endpoint verification.\n'
       '- Access allow/deny lists: `AGENT_ACCESS_POLICY.json` (agent-facing rules in `.opencode/team/ACCESS_RULES.md`).\n'
       '- Network/filesystem: instructions and tool permissions are NOT OS security boundaries.\n'
       '- Git: local branches/commits coordinated by orchestrator, push according to policy.\n'
       '- A confidential project requires verified local inference and OS isolation where appropriate.\n'
       '- Substantial architecture changes and large resource increases require user authorization.\n')
    write_text(project/'PROJECT_POLICY.md',policy)
    say(f'\nKlart: {len(selected)} agenter installerade i {project}.')
    say('Projektets konfiguration och tidigare filer har säkerhetskopierats vid ändring.')
    say('OBS: eventuella .opencode/agent-filer/andra överordnade globala regler kontrolleras separat av OpenCode.')

def configure(project, mode='full'):
    if not project.exists():
        if confirm(f'Skapa projektkatalog {project}?',False): project.mkdir(parents=True)
        else: raise RuntimeError('Projektet finns inte')
    git=project/'.git'
    if not git.exists() and mode=='full':
        if confirm('Projektet saknar Git-repo. Initiera med git init?',True):
            subprocess.run(['git','init',str(project)],check=True)
    manifest=read_manifest(project)
    old=manifest.get('installed_agents',[])
    available=profiles()
    selected=select_agents(available,old) if mode in ('full','agents') else list(old)
    if not selected: raise RuntimeError('Projektet saknar ett registrerat team. Välj Installera först.')
    cfg=json_load(project/'opencode.json')
    oldmodels={n:(cfg.get('agent',{}).get(n,{}) or {}).get('model') for n in selected}
    existing_models=manifest.get('models',{})
    oldmodels={n:(oldmodels.get(n) or existing_models.get(n)) for n in selected}
    models=oldmodels
    if mode in ('full','models','agents'):
        if not confirm('Kör opencode models och välj modell för varje vald agent?',True):
            raise RuntimeError('Modellval krävs för nya installationer. Avbrutet.')
        say('OpenCode kan hämta katalogen över nätverket. Enbart denna begäran om modellista görs av verktyget.')
        if not confirm('Tillåt opencode models nu?',True): raise RuntimeError('Modellista ej godkänd')
        models=assign_models(selected,list_models(project),oldmodels)
    if mode in ('full','permissions'):
        classif=choose_mode() if mode=='full' else manifest.get('mode','PRIVATE')
        perms=permission_wizard(manifest.get('permissions'))
    else:
        classif=manifest.get('mode','PRIVATE')
        perms=manifest.get('permissions') or permission_wizard()
    if classif=='PRIVATE':
        say('PRIVATE: verktyget kan inte bevisa att valda modeller körs lokalt.')
        if mode in ('models','agents') and not confirm('Bekräftar du att samtliga nu valda modeller verkligen körs lokalt och inte skickar data till molnet?',False):
            raise RuntimeError('Modelländringen i PRIVATE avbruten')
    access=load_policy(project/ACCESS_FILE) if (project/ACCESS_FILE).exists() else default_access_policy(project,perms)
    if mode in ('full','permissions') and confirm('Redigera whitelist/blacklist för kataloger och internet nu?',False):
        access=access_wizard(project,access)
    say('\n=== Sammanfattning ===')
    say(f'Projekt: {project}; Agenter: {len(selected)}; Sekretess: {classif}; Shell: {perms["shell"]}; Push: {perms["gitpush"]}; Internet: {perms["internet"]}')
    for n in selected: say(f'  {n:27} {models.get(n) or "INHERIT"}')
    if not confirm('Spara projektkonfiguration och profiler?',False): return
    apply(project,selected,models,perms,classif,access=access)

def sync_access(project):
    if not read_manifest(project):raise RuntimeError('Installera agentteamet i projektet först.')
    access=load_policy(project/ACCESS_FILE)
    if Path(access['project_root']).resolve()!=project.resolve():
        raise RuntimeError('project_root i policyn överensstämmer inte med projektkatalogen')
    cfg=json_load(project/'opencode.json')
    manifest=read_manifest(project)
    cfg['permission']=make_permission({**manifest.get('permissions',{}),'_selected_agents':manifest.get('installed_agents',[])},access)
    ins=cfg.get('instructions',[])
    if not isinstance(ins,list):raise RuntimeError('instructions måste vara en lista')
    if ACCESS_RULES not in ins:ins.append(ACCESS_RULES)
    cfg['instructions']=ins
    write_text(project/ACCESS_RULES,render_access_rules(access))
    (project/'.opencode/tools').mkdir(parents=True,exist_ok=True)
    write_text(project/'.opencode/tools/access_check.py',(ROOT/'access_check.py').read_text(encoding='utf-8'))
    write_text(project/'.opencode/tools/access_fetch.py',(ROOT/'access_fetch.py').read_text(encoding='utf-8'))
    write_json(project/'opencode.json',cfg)
    say('Policy synkroniserad. Starta om OpenCode för att läsa in nya regler.')


def configure_access(project):
    manifest=read_manifest(project)
    if not manifest:raise RuntimeError('Installera agentteamet i projektet först.')
    current=load_policy(project/ACCESS_FILE) if (project/ACCESS_FILE).exists() else default_access_policy(project,manifest.get('permissions',{}))
    new=access_wizard(project,current)
    cfg=json_load(project/'opencode.json')
    cfg['permission']=make_permission({**manifest.get('permissions',{}),'_selected_agents':manifest.get('installed_agents',[])},new)
    ins=cfg.get('instructions',[])
    if ACCESS_RULES not in ins:ins.append(ACCESS_RULES)
    cfg['instructions']=ins
    write_json(project/ACCESS_FILE,new)
    write_text(project/ACCESS_RULES,render_access_rules(new))
    (project/'.opencode/tools').mkdir(parents=True,exist_ok=True)
    write_text(project/'.opencode/tools/access_check.py',(ROOT/'access_check.py').read_text(encoding='utf-8'))
    write_text(project/'.opencode/tools/access_fetch.py',(ROOT/'access_fetch.py').read_text(encoding='utf-8'))
    write_json(project/'opencode.json',cfg)
    say('Åtkomstpolicyn är uppdaterad. Starta om OpenCode för att ladda nya instruktioner och behörigheter.')


def create_agent():
    say('\n=== Skapa ny återanvändbar agentprofil ===')
    slug=prompt('Agentnamn (ex. mechanical-engineer)')
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,54}',slug):
        raise RuntimeError('Namnet måste vara gemener, siffror eller bindestreck och minst 3 tecken.')
    if (PROFILES/(slug+'.md')).exists() or (CUSTOM/(slug+'.md')).exists():
        raise RuntimeError('Agenten finns redan. Redigera dess fil manuellt i custom-profiles.')
    desc=prompt('Beskrivning (på engelska)')
    if not desc: raise RuntimeError('Beskrivning krävs')
    say('Skriv instruktioner på engelska, avsluta med en ensam punkt på en rad.')
    lines=[]
    while True:
        line=input()
        if line.strip()=='.': break
        lines.append(line)
    if not lines: raise RuntimeError('Agentinstruktioner krävs')
    CUSTOM.mkdir(parents=True,exist_ok=True)
    profile=(f'---\ndescription: {json.dumps(desc,ensure_ascii=False)}\nmode: subagent\n---\n\n'
      '# '+slug+'\n\n'+'\n'.join(lines)+'\n\n'
      'Follow the project-wide team rules. Admit uncertainty, request suitable expertise, and keep handoffs concise.\n')
    write_text(CUSTOM/(slug+'.md'),profile)
    say(f'Agenten sparad centralt: {CUSTOM/(slug+".md")}')
    say('Välj nu Installera/Uppdatera i projektet för att inkludera den och välja en modell.')

def status(project):
    info=read_manifest(project)
    if not info:
        say('Ingen v2-manifest hittad. Använd Installera för att migrera ett äldre projekt.'); return
    say(f'Åtkomstpolicy: {project/ACCESS_FILE} (INTE en sandbox)')
    say(f'Projekt: {project}\nInstallerat: {info.get("version")}\nKlassning: {info.get("mode")}\nAgenter ({len(info.get("installed_agents",[]))}):')
    for n in info.get('installed_agents',[]):
        say(f'  {n:27} {info.get("models",{}).get(n) or "inherit"}')
    v=info.get('permissions',{})
    for name in ('shell','file_edit','gitpush','internet','outside_read','outside_write','sudo','destructive','secrets','mcp','packages','hardware','unattended'):
        say(f'  {name:15}: {v.get(name)}')

def run_opencode(project, resume=False):
    if not shutil.which('opencode'): raise RuntimeError('opencode saknas i PATH')
    info=read_manifest(project)
    cmd=['opencode']
    if resume: cmd.append('--continue')
    if info.get('permissions',{}).get('unattended'):
        say('VARNING: --auto godkänner ASK-regler. Uttryckliga DENY gäller fortfarande; shell är inte sandbox.')
        cmd.append('--auto')
    say('Startar: '+' '.join(cmd))
    os.chdir(project)
    os.execvp(cmd[0],cmd)

def menu():
    while True:
        say('\n=== agents-opencode v'+VERSION+' ===')
        say(' 1) Installera / konfigurera ett projekt (välj agenter + modeller + behörigheter)')
        say(' 2) Ändra alla agentmodeller från hela opencode models-listan')
        say(' 3) Välj / ta bort agenter i projektet')
        say(' 4) Ändra projektets behörighetsguide')
        say(' 5) Visa projektstatus')
        say(' 6) Skapa en ny agentprofil (återanvändbar)')
        say(' 7) Starta OpenCode')
        say(' 8) Fortsätt senaste OpenCode-session')
        say(' 9) Lista tillgängliga modeller')
        say('10) Redigera fil- och nätverkslistor (whitelist/blacklist)')
        say('11) Synkronisera manuellt redigerad access-policy')
        say(' 0) Avsluta')
        n=prompt('Välj','0')
        if n=='0': return
        try:
            if n=='6': create_agent(); continue
            project=project_dir()
            if n=='1': configure(project,'full')
            elif n=='2': configure(project,'models')
            elif n=='3': configure(project,'agents')
            elif n=='4': configure(project,'permissions')
            elif n=='5': status(project)
            elif n=='7': run_opencode(project)
            elif n=='8': run_opencode(project,True)
            elif n=='10':configure_access(project)
            elif n=='11':sync_access(project)
            elif n=='9':
                if confirm('Tillåt opencode models (kan kontakta modellkatalogen)?',False):
                    for m in list_models(project): say(m)
        except (RuntimeError,ValueError,EOFError,KeyboardInterrupt,subprocess.SubprocessError) as e:
            say('\nFel/avbrutet: '+str(e))

def main():
    args=sys.argv[1:]
    if not args: return menu()
    cmd=args[0]
    if cmd in ('--help','help','-h'):
        say('agents-opencode [install|models-all|agents|permissions|access|sync-access|status|add-agent|run|resume|list-models] [PROJECT_PATH]')
        say('Installation: bash install.sh (användarnivå, ~/.local/bin). Ingen modell är förvald.')
        return
    if cmd in ('--version','-V'): say(VERSION); return
    if cmd=='add-agent': create_agent(); return
    project=Path(args[1]).expanduser().resolve() if len(args)>1 else Path.cwd().resolve()
    if cmd in ('install','init'): configure(project,'full')
    elif cmd in ('models-all','models'): configure(project,'models')
    elif cmd=='agents': configure(project,'agents')
    elif cmd=='permissions': configure(project,'permissions')
    elif cmd=='access': configure_access(project)
    elif cmd=='sync-access': sync_access(project)
    elif cmd=='status': status(project)
    elif cmd=='run': run_opencode(project)
    elif cmd=='resume': run_opencode(project,True)
    elif cmd=='list-models':
        if confirm('Tillåt opencode models (kan kontakta modellkatalogen)?',False):
            for x in list_models(project): say(x)
    else: raise RuntimeError('Okänt kommando. agents-opencode --help')

if __name__=='__main__':
    try: main()
    except (RuntimeError,KeyboardInterrupt,EOFError) as ex:
        print('ERROR: '+str(ex),file=sys.stderr); sys.exit(1)
