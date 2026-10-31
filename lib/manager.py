#!/usr/bin/env python3
"""OpenCode v1.x portable user-level agent team installer. Python stdlib only.
The user-facing command is the installed `agents-opencode` launcher.
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
from access_check import load_policy, validate, path_decision, url_decision, is_filesystem_root, absolute_policy_path
from i18n import set_language, get_language, select_language, tr

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
    hint = tr('J/n', 'Y/n') if default else tr('j/N', 'y/N')
    while True:
        ans = input(f'{msg} [{hint}]: ').strip().lower()
        if not ans: return default
        if ans in ('j','ja','y','yes'): return True
        if ans in ('n','nej','no'): return False
        say(tr('Svara j eller n.', 'Answer y or n.'))

def choose(msg, options, default=''):
    for k, desc in options: say(f'  {k}) {desc}')
    accepted = {k for k,_ in options}
    while True:
        ans=prompt(msg,default)
        if ans in accepted: return ans
        say(tr('Ogiltigt val.', 'Invalid choice.'))

def policy_action(title, default):
    d = {'allow':'a','ask':'q','deny':'d'}[default]
    return ACTIONS[choose(title, [('a',tr('Tillåt utan fråga','Allow without asking')),('q',tr('Fråga varje gång','Ask every time')),('d',tr('Neka','Deny'))],d)]


def action_label(value):
    if isinstance(value, bool): return tr('ja','yes') if value else tr('nej','no')
    return {'allow':tr('tillåt','allow'), 'ask':tr('fråga','ask'), 'deny':tr('neka','deny')}.get(value, value)

def project_dir(arg=None):
    value=arg if arg else prompt(tr('Projektkatalog','Project directory'),str(Path.cwd()))
    return require_local_project(value)


def require_local_project(value):
    """Team installations belong to a project, never a home/global agent layer."""
    project=Path(value).expanduser().resolve()
    home=Path.home().resolve()
    global_dirs=[home/'.opencode',home/'.config/opencode',
                 Path(os.environ.get('XDG_CONFIG_HOME') or home/'.config')/'opencode']
    if os.environ.get('APPDATA'):
        global_dirs.append(Path(os.environ['APPDATA'])/'opencode')
    if os.environ.get('OPENCODE_CONFIG_DIR'):
        global_dirs.append(Path(os.environ['OPENCODE_CONFIG_DIR']).expanduser())
    if project==home or project.parent==project or any(
            project.is_relative_to(p.resolve()) for p in global_dirs):
        raise RuntimeError(tr('Välj en lokal projektkatalog, inte hemkatalogen eller OpenCodes globala konfiguration.',
                              'Choose a local project directory, not the home directory or OpenCode global configuration.'))
    targets=['AGENTS.md','PROJECT_POLICY.md',ACCESS_FILE,'opencode.json',str(MANIFEST),
             '.opencode','.opencode/agents','.opencode/team','.opencode/tools',
             ACCESS_RULES,'.opencode/tools/access_check.py','.opencode/tools/access_fetch.py']
    targets += ['.opencode/team/'+name for name in ('TEAM_RULES.md','WORKFLOW.md','HANDOFF_TEMPLATE.md')]
    targets += [str(p.relative_to(project)) for p in (project/'.opencode/agents').glob('*.md')]
    for name in targets:
        if not (project/name).resolve().is_relative_to(project):
            raise RuntimeError(tr('Installationsfilen pekar utanför projektet: ','Installation path points outside the project: ')+name)
    return project

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
    say(tr('\n=== Välj vilka agenter som ska installeras ===','\n=== Choose agents to install ==='))
    for i,name in enumerate(ids,1):
        tick = '*' if (old and name in old) else ' '
        say(f'{i:>2}) [{tick}] {name:26} {titles(available[name])}')
    say(tr('\nAnge a = alla, c = kärnteamet, siffror (ex. 1,3,6-9) eller Enter för tidigare val.','\nEnter a = all, c = core team, numbers (e.g. 1,3,6-9), or Enter for previous selection.'))
    while True:
        answer=prompt(tr('Agenter','Agents'), tr('föregående','previous') if old else 'c')
        if answer=='a': selected=ids
        elif answer=='c': selected=[x for x in ('orchestrator','system-architect','technical-documenter') if x in available]
        elif answer==tr('föregående','previous') and old: selected=[x for x in ids if x in old]
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
                say(tr('Ogiltig lista. Exempel: a, c, 1,3,6-9','Invalid list. Examples: a, c, 1,3,6-9')); continue
        if selected:
            say(tr('Valt {count}: ','Selected {count}: ').format(count=len(selected))+', '.join(selected))
            if 'orchestrator' not in selected:
                say(tr('OBS: Orkestreraren saknas. Du måste själv leda teamet eller välja en annan huvudagent.','NOTE: No orchestrator selected. Lead the team yourself or choose another primary agent.'))
            if confirm(tr('Använd detta urval?','Use this selection?'),True): return selected
        else: say(tr('Välj minst en agent.','Choose at least one agent.'))


def opencode_command(arguments=(), executable=None, windows=None):
    """Resolve the actual executable; batch shims accept only fixed manager flags.

    cmd.exe needs its own outer quotes for a quoted executable with spaces.
    No project path or other user input is interpolated into the shell command.
    Reject shell metacharacters even in the resolved shim path (fail closed).
    """
    allowed = {'models', '--continue', '--auto'}
    if any(arg not in allowed for arg in arguments):
        raise ValueError(tr('Otillåtet OpenCode-argument','Unsupported OpenCode argument'))
    executable = executable or shutil.which('opencode')
    if not executable:
        raise RuntimeError(tr('opencode saknas i PATH; installera/autentisera OpenCode först.',
                              'opencode is not in PATH; install/authenticate OpenCode first.'))
    windows = os.name == 'nt' if windows is None else windows
    if windows and executable.lower().endswith(('.cmd', '.bat')):
        if any(c in executable for c in '\r\n"%!' + '&|<>^'):
            raise RuntimeError(tr('Osäker sökväg till OpenCode-kommandofil','Unsafe OpenCode batch shim path'))
        command = '""' + executable + '"' + ''.join(' ' + a for a in arguments) + '"'
        # A list would go through subprocess.list2cmdline, whose backslash quote
        # escaping is for C argv parsers, NOT cmd.exe's /c grammar. Supply the
        # exact CreateProcess command line instead (still shell=False).
        interpreter = shutil.which('cmd.exe') or 'cmd.exe'
        return subprocess.list2cmdline([interpreter]) + ' /d /s /c ' + command
    return [executable, *arguments]

def list_models(cwd):
    # Test hook: no runtime dependency on mock data. Real installations call OpenCode.
    fixture=os.getenv('AGENTS_OPENCODE_TEST_MODELS_FILE')
    if fixture:
        text=Path(fixture).read_text()
    else:
        cmd=opencode_command(['models'])
        say(tr('\nHämtar modellistan med: opencode models','\nFetching model list with: opencode models'))
        r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=90)
        if r.returncode: raise RuntimeError(tr('opencode models misslyckades:\n','opencode models failed:\n')+r.stderr[-1000:])
        text=r.stdout
    result=[]
    for line in text.splitlines():
        value=line.strip()
        if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_./:@-]*',value):
            if value not in result: result.append(value)
    if not result: raise RuntimeError(tr('Inga modell-ID hittades i opencode models.','No model IDs found in opencode models.'))
    return result

def pick_model(name, catalog, old=None, previous=None):
    say(tr('\n=== Modell för {name} ===','\n=== Model for {name} ===').format(name=name))
    say(tr('Nuvarande: {old}. Alla {count} modeller visas:','Current: {old}. All {count} models are shown:').format(old=old or tr('ingen vald','none selected'), count=len(catalog)))
    for i,m in enumerate(catalog,1): say(f'{i:>3}) {m}')
    hints=[]
    if old: hints.append(tr('Enter = behåll','Enter = keep'))
    if previous: hints.append(tr('p = använd föregående val','p = use previous choice'))
    hints.append(tr('i = ärv från anropande agent','i = inherit from calling agent'))
    say(' | '.join(hints))
    while True:
        v=prompt(tr('Modellnummer','Model number'))
        if not v and old: return old
        if v.lower()=='i': return None
        if v.lower()=='p' and previous: return previous
        if v.isdigit() and 1<=int(v)<=len(catalog):
            m=catalog[int(v)-1]
            if name=='image-analyst': say(tr('OBS: kontrollera att modellen verkligen har stöd för bildinmatning.','NOTE: verify that the model actually supports image input.'))
            return m
        say(tr('Ange ett nummer från listan','Enter a number from the list')+(tr(', p, i eller Enter',', p, i or Enter') if old else tr(', p eller i',', p or i'))+'.')

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
        if not isinstance(v,dict): raise ValueError(tr('Roten måste vara ett objekt','Root must be an object'))
        return v
    except (ValueError,UnicodeError) as ex:
        raise RuntimeError(tr('{path} kunde inte läsas som vanlig JSON. Gör om JSONC till JSON innan ändring: {ex}','{path} could not be read as plain JSON. Convert JSONC to JSON before editing: {ex}').format(path=path,ex=ex))

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
    say(tr('\n=== Projektets informationsklassning ===','\n=== Project data classification ==='))
    k=choose(tr('Välj klassning','Choose classification'),[('1',tr('PRIVATE: endast godkända lokala modellanslutningar','PRIVATE: approved local model connections only')),('2',tr('SHAREABLE: godkända molnmodeller, projektets tillåtna data','SHAREABLE: approved cloud models, permitted project data')),('3',tr('HYBRID: lokal + moln; sekretess måste hanteras separat','HYBRID: local + cloud; confidentiality must be handled separately'))],'1')
    mode={'1':'PRIVATE','2':'SHAREABLE','3':'HYBRID'}[k]
    if mode=='PRIVATE':
        say(tr('KRITISKT: verktyget kan inte avgöra om en provider faktiskt vidarebefordrar data till molnet.','CRITICAL: this tool cannot determine whether a provider forwards data to the cloud.'))
        if not confirm(tr('Bekräftar du att ALLA valda modeller verkligen är lokalt hostade och att projektet får skickas till dessa endpoints?','Do you confirm ALL selected models are actually hosted locally and this project may be sent to those endpoints?'),False):
            raise RuntimeError(tr('PRIVATE kräver verifierad lokal modellanslutning. Avbrutet.','PRIVATE requires verified local model connections. Cancelled.'))
    else:
        if not confirm(tr('Får godkända molnmodeller behandla den delbara källkod och kontext som ligger i projektet?','May approved cloud models process the shareable source code and context in this project?'),False):
            raise RuntimeError(tr('Molnbehandling inte godkänd. Avbrutet.','Cloud processing not approved. Cancelled.'))
    return mode

def ask_mounts():
    mounts=[]
    say(tr('Ange absoluta katalogsökvägar för tillåtna nätverksdiskar. Tom rad avslutar.','Enter absolute directory paths for permitted network shares. A blank line finishes.'))
    while True:
        val=prompt(tr('Monterad katalog (eller Enter)','Mounted directory (or Enter)'))
        if not val: break
        try:
            p=absolute_policy_path(val).resolve()
        except ValueError:
            say(tr('Ange en absolut sökväg utan enhetsnamnrymder.','Enter an absolute path without device namespaces.'))
            continue
        if not p.is_dir() or not p.is_absolute(): say(tr('Katalogen måste finnas som en absolut sökväg.','The directory must exist at an absolute path.')); continue
        r=policy_action(tr('Läsa {path}','Read {path}').format(path=p), 'allow')
        w=policy_action(tr('Skriva {path}','Write {path}').format(path=p), 'deny')
        mounts.append({'path':str(p),'read':r,'write':w})
    return mounts

def permission_wizard(existing=None):
    say(tr('\n=== Behörighetsguide ===','\n=== Permission wizard ==='))
    presets={
      '1':dict(shell='ask',file_edit='ask',gitpush='deny',internet='deny',outside_read='deny',outside_write='deny',sudo='deny',destructive='deny',secrets='deny',mcp='deny',packages='deny',hardware='deny',unattended=False),
      '2':dict(shell='allow',file_edit='allow',gitpush='ask',internet='ask',outside_read='deny',outside_write='deny',sudo='deny',destructive='ask',secrets='deny',mcp='ask',packages='ask',hardware='deny',unattended=False),
      '3':dict(shell='allow',file_edit='allow',gitpush='allow',internet='allow',outside_read='allow',outside_write='allow',sudo='allow',destructive='allow',secrets='ask',mcp='allow',packages='allow',hardware='ask',unattended=True)
    }
    say(tr('Förinställningar ändrar bara behörigheter, ALDRIG modellval.','Presets change permissions only, NEVER model choices.'))
    n=choose(tr('Startläge','Starting preset'),[('1',tr('Låst arbetsdator','Locked-down workstation')),('2',tr('Utvecklingsdator','Development workstation')),('3',tr('Isolerad VM med stora rättigheter','Isolated VM with broad permissions')),('4',tr('Utgå från projektets nuvarande behörigheter','Use current project permissions'))], '4' if existing else '2')
    base=dict(existing) if n=='4' and existing else dict(presets.get(n,presets['2']))
    say(tr('\nJustera vart och ett av valen (a=allow, q=ask, d=deny):','\nAdjust each setting (a=allow, q=ask, d=deny):'))
    # Repair older v2 manifests that do not contain newly introduced controls.
    for k,default in [('file_edit','allow'),('mcp','ask'),('packages','ask'),('hardware','deny')]: base.setdefault(k,default)
    base['shell']=policy_action(tr('Shellkommandon generellt','Shell commands in general'),base['shell'])
    base['file_edit']=policy_action(tr('Skriva/redigera projektfiler genom OpenCodes filverktyg','Write/edit project files through OpenCode file tools'),base['file_edit'])
    base['gitpush']=policy_action(tr('Git push mot remote','Git push to remote'),base['gitpush'])
    base['internet']=policy_action(tr('Internet via OpenCode webfetch/websearch + direkt curl/wget/ssh i shell','Internet via OpenCode webfetch/websearch + direct curl/wget/ssh in shell'),base['internet'])
    base['outside_read']=policy_action(tr('Läsa utanför projektmappen med OpenCodes filverktyg','Read outside the project with OpenCode file tools'),base['outside_read'])
    base['outside_write']=policy_action(tr('Skriva utanför projektmappen med OpenCodes filverktyg','Write outside the project with OpenCode file tools'),base['outside_write'])
    base['sudo']=policy_action(tr('Sudo och privilegierade kommandon','Sudo and privileged commands'),base['sudo'])
    base['destructive']=policy_action(tr('Potentiellt destruktiva shellkommandon','Potentially destructive shell commands'),base['destructive'])
    base['secrets']=policy_action(tr('Läsa hemligheter/nyckelfiler med filverktyg','Read secrets/key files with file tools'),base['secrets'])
    base['mcp']=policy_action(tr('Anropa externa MCP-verktyg och anslutna externa tjänster','Call external MCP tools and connected external services'),base['mcp'])
    base['packages']=policy_action(tr('Installera system- eller språkpaket via vanliga kommandomönster','Install system or language packages through common command patterns'),base['packages'])
    base['hardware']=policy_action(tr('Firmwareflashning och verktyg för hårdvarusändning (best effort)','Firmware flashing and hardware transmission tools (best effort)'),base['hardware'])
    base['mounts']=ask_mounts() if confirm(tr('Konfigurera specifika nätverksdiskar nu?','Configure specific network shares now?'),bool(base.get('mounts'))) else base.get('mounts',[])
    say(tr('\nObevakad körning med --auto godkänner även regler som annars skulle fråga.','\nUnattended execution with --auto also approves rules that would otherwise ask.'))
    base['unattended']=confirm(tr('Aktivera obevakat läge för detta projekt?','Enable unattended mode for this project?'),bool(base.get('unattended')))
    if base['shell']=='allow':
        say(tr('VARNING: shell=allow är lika med värdanvändarens åtkomst. Python, byggskript och Git-hooks kan kringgå mönsterregler för filer/nätverk.','WARNING: shell=allow grants the host user’s access. Python, build scripts and Git hooks can bypass file/network patterns.'))
    if base['unattended'] and any(base[k]=='ask' for k in ('gitpush','internet','outside_read','outside_write','sudo','destructive','secrets','packages','hardware','mcp')):
        say(tr('VARNING: --auto godkänner ASK. Ändra till DENY om en åtgärd verkligen ska förbli blockerad obevakat.','WARNING: --auto approves ASK. Use DENY if an action must remain blocked when unattended.'))
    if base['shell']=='allow' and base['outside_read']=='deny':
        say(tr('VARNING: utanför-projekt=deny skyddar inte mot shellkommandon med rättigheter på värdsystemet.','WARNING: outside-project=deny does not protect against shell commands with host-system permissions.'))
    if not confirm(tr('Bekräfta denna behörighetsprofil?','Confirm this permission profile?'),False): raise RuntimeError(tr('Behörighetskonfiguration avbruten','Permission configuration cancelled'))
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
    python = 'python' if os.name == 'nt' else 'python3'
    example = 'C:/absolute/path' if os.name == 'nt' else '/absolute/path'
    lines=['# Agent access rules (project-specific, mandatory instructions)', '',
       '**WARNING: ADVISORY, NOT ACTUAL SECURITY.** These rules describe authorized behavior, not an operating-system sandbox.',
       'A permitted shell command, program, symlink, Git hook or plugin can bypass these rules. Never interpret this document as technical isolation.',
       f'Before accessing resources, consult `AGENT_ACCESS_POLICY.json`. When unsure, use `{python} .opencode/tools/access_check.py path read {example}`,',
       f'`{python} .opencode/tools/access_check.py path write {example}`, or `{python} .opencode/tools/access_check.py url https://host/path`.',
       'These checks are advisory and do not perform the operation. Deny means stop; ask means request user authorization (do not treat --auto as approval to expand the policy).',
       f'For explicitly allowed public HTTP(S) sites, `{python} .opencode/tools/access_fetch.py https://allowed-host/path` can retrieve up to 2 MiB (GET only; no redirects).',
       'Never rewrite the policy or this document as a workaround. Request changes from the owner through agents-opencode.',
       '', '## Filesystem',
       '- The project directory is permitted for normal project work. Filesystem roots (POSIX `/`, Windows drive roots and UNC share roots) and all other locations are **denied by default** unless explicitly allowed below.',
       '- Resolved paths (including symlinks) count; a mount can be read-only independently of local paths.',
       f"- Outside defaults: read={fs['default_outside']['read'].upper()}, write={fs['default_outside']['write'].upper()}." ]
    if os.name == 'nt':
        lines.append('- Windows: use Python 3 as `python` (or `py -3` if needed). Drive/UNC path patterns and command restrictions are best effort; PowerShell, cmd.exe, batch shims and alternate path spellings can bypass them. Use OS isolation for enforcement.')
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
    say(tr('\n=== Åtkomstpolicy: whitelist / blacklist (INTE en säker sandbox) ===','\n=== Access policy: allowlist / denylist (NOT a secure sandbox) ==='))
    say(tr('Projektmappen tillåts. Filsystemrötter och övriga kataloger nekas som standard.','The project directory is allowed. Filesystem roots and other directories are denied by default.'))
    fs=access['filesystem']; net=access['network']
    if confirm(tr('Ändra standardåtkomst utanför projektet?','Change default access outside the project?'),False):
        fs['default_outside']['read']=policy_action(tr('Standard: läsa utanför projektet','Default: read outside project'),fs['default_outside']['read'])
        fs['default_outside']['write']=policy_action(tr('Standard: skriva utanför projektet','Default: write outside project'),fs['default_outside']['write'])
    if confirm(tr('Ange tillåtna/blockerade lokala kataloger eller nätverksdiskar?','Specify allowed/blocked local directories or network shares?'),False):
        say(tr('Ange absolut sökväg. Varje katalogregel omfattar även underkataloger. Tomt avslutar.','Enter an absolute path. Each directory rule includes subdirectories. Blank finishes.'))
        while True:
            value=prompt(tr('Sökväg','Path'))
            if not value: break
            try:
                path=str(absolute_policy_path(value).resolve())
            except ValueError:
                say(tr('Ange en absolut sökväg utan enhetsnamnrymder.','Enter an absolute path without device namespaces.'))
                continue
            if is_filesystem_root(path):
                say(tr('En explicit allow för en filsystemrot stöds inte. Välj bred VM-standard om den nivån av åtkomst behövs.','Explicit allow for a filesystem root is not supported. Choose broad VM defaults if that level of access is needed.')); continue
            kind=choose(tr('Typ','Type'),[('1',tr('Lokal sökväg','Local path')),('2',tr('Monterad nätverksdisk','Mounted network share'))],'1')
            r=policy_action(tr('Läsa','Read'), 'allow'); w=policy_action(tr('Skriva','Write'),'deny')
            fs['paths']=[x for x in fs['paths'] if x['path']!=path]
            fs['paths'].append({'path':path,'kind':'network-share' if kind=='2' else 'local','read':r,'write':w})
        if fs['paths'] and confirm(tr('Ta bort någon befintlig katalogregel?','Remove an existing directory rule?'),False):
            for i,x in enumerate(fs['paths'],1): say(f'{i}) {x["path"]} ({action_label(x["read"])}/{action_label(x["write"])})')
            number=prompt(tr('Nummer (Enter=ingen)','Number (Enter=none)'))
            if number.isdigit() and 1<=int(number)<=len(fs['paths']):fs['paths'].pop(int(number)-1)
    if confirm(tr('Ändra standardåtkomst för agenters internetanrop?','Change default access for agent internet requests?'),False):
        net['default']=policy_action(tr('Standard: internet','Default: internet'),net['default'])
    if confirm(tr('Ange tillåtna/blockerade internetvärdar?','Specify allowed/blocked internet hosts?'),False):
        say(tr('Ange värdnamn, t.ex. docs.python.org eller *.example.org. Tomt avslutar.','Enter a hostname, e.g. docs.python.org or *.example.org. Blank finishes.'))
        while True:
            host=prompt(tr('Värdnamn','Hostname'))
            if not host: break
            if '/' in host or any(c.isspace() for c in host):
                say(tr('Endast värdnamn, inte hel URL.','Hostname only, not a full URL.')); continue
            scheme=choose(tr('Protokoll','Protocol'),[('1','https'),('2','http'),('3','ssh')],'1')
            port=prompt(tr('Port, Enter = standard','Port, Enter = default'))
            if port and (not port.isdigit() or not 1<=int(port)<=65535):say(tr('Ogiltig port','Invalid port')); continue
            action=policy_action(tr('Åtkomst','Access'), 'allow')
            entry={'host':host.lower(),'scheme':{'1':'https','2':'http','3':'ssh'}[scheme],'access':action}
            if port:entry['port']=int(port)
            net['hosts']=[r for r in net['hosts'] if (r['host'],r.get('scheme'),r.get('port'))!=(entry['host'],entry['scheme'],entry.get('port'))]
            net['hosts'].append(entry)
        if net['hosts'] and confirm(tr('Ta bort någon befintlig värdregel?','Remove an existing host rule?'),False):
            for i,x in enumerate(net['hosts'],1):say(f'{i}) {x.get("scheme","https")}://{x["host"]} {action_label(x["access"])}')
            number=prompt(tr('Nummer (Enter=ingen)','Number (Enter=none)'))
            if number.isdigit() and 1<=int(number)<=len(net['hosts']):net['hosts'].pop(int(number)-1)
    validate(access)
    say(tr('OBS: denna fil är en beteendepolicy; utan OS-sandbox kan shellkommandon kringgå den.','NOTE: this file is a behavioral policy; without an OS sandbox shell commands can bypass it.'))
    if not confirm(tr('Spara dessa åtkomstregler?','Save these access rules?'),False): raise RuntimeError(tr('Åtkomstguiden avbruten','Access wizard cancelled'))
    return access

def path_patterns(path):
    """Best-effort native + forward-slash spellings; no new permission schema."""
    path = str(path).rstrip('/\\')
    variants = [path]
    if re.match(r'^[A-Za-z]:', path) or path.startswith(('\\\\', '//')):
        variants += [path.replace('\\', '/'), path.replace('/', '\\')]
    return list(dict.fromkeys(pat for p in variants for pat in
                             (p, p + ('\\*' if '\\' in p else '/*'),
                              p + ('\\**' if '\\' in p else '/**'))))


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
    # OpenCode wildcard matching is not a shell glob: avoid character classes
    # such as [A-Za-z], which some versions treat as literal text.
    absolute_patterns = ('/*', '*:/*', '*:\\*', '//*/**', '\\\\*')
    for pat in absolute_patterns:
        read[pat]=v['outside_read']; edit[pat]=v['outside_write']
    for m in v.get('mounts',[]):
        for pat in path_patterns(m['path']):
            ext[pat]='allow' if 'allow' in (m['read'],m['write']) else ('ask' if 'ask' in (m['read'],m['write']) else 'deny')
            read[pat]=m['read']; edit[pat]=m['write']
    if access:
        # Native OpenCode v1.x external-directory and read/edit guards are best effort.
        fs=access['filesystem']; net=access['network']
        ext['*']='allow' if 'allow' in fs['default_outside'].values() else ('ask' if 'ask' in fs['default_outside'].values() else 'deny')
        for pat in absolute_patterns:
            read[pat]=fs['default_outside']['read']
            edit[pat]=fs['default_outside']['write']
        # Explicit project-root exception avoids rejecting absolute paths within the worktree.
        for pat in path_patterns(access['project_root']):
            read[pat]='allow'
            edit[pat]=v.get('file_edit','allow')
        for r in sorted(fs.get('paths',[]),key=lambda x:len(re.split(r'[/\\]+',x['path']))):
            for pat in path_patterns(r['path']):
                ext[pat]='allow' if 'allow' in (r['read'],r['write']) else ('ask' if 'ask' in (r['read'],r['write']) else 'deny')
                read[pat]=r['read']; edit[pat]=r['write']
        # OpenCode v1.x cannot implement webfetch host allowlists. Avoid unintentionally broad allow.
        network_safe=net['default'] if not net.get('hosts') else 'deny'
        v={**v,'_webfetch_permission':network_safe}
    # Never let the agent rewrite its own access policy via direct edit tools.
    if access and any(r['access']=='allow' and r.get('scheme','https') in ('https','http') for r in access['network'].get('hosts',[])):
        shell['python3 .opencode/tools/access_fetch.py *']='allow'
        if os.name == 'nt':
            shell['python .opencode/tools/access_fetch.py *']='allow'
    for pat in (ACCESS_FILE, ACCESS_RULES, '.opencode/tools/access_check.py', '.opencode/tools/access_fetch.py'):
        edit[pat]='deny'
        if access:
            for absolute in path_patterns(access['project_root'].rstrip('/\\')+'/'+pat):
                edit[absolute]='deny'
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
       'architect/documenter consultation is need-based, not an implementation gate. '
       'Follow `.opencode/team/TEAM_RULES.md`, `.opencode/team/WORKFLOW.md`, `PROJECT_POLICY.md` and `AGENT_ACCESS_POLICY.json`.\n'
       'Implement, verify, integrate and continue through feasible authorized work. A checkpoint, commit, '
       'version boundary or specialist handoff is not a stopping condition. Do not invent approval gates.\n'
       'Use compact active memory in the repository-designated local work area; read history selectively. '
       'The primary coordinates delegation; collaborator lists do not authorize nested agent calls.\n'
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
            say(tr('VARNING: AGENTS.md har äldre agentteam-regler som inte kunde identifieras exakt. Kontrollera konflikter manuellt.','WARNING: AGENTS.md contains older team rules that could not be identified exactly. Check for conflicts manually.'))
        text=text.rstrip()+'\n\n'+new+'\n'
    write_text(file,text)

def sync_team_files(project, selected):
    """Copy maintained sources without changing models, access policy or active memory."""
    project=require_local_project(project)
    available=profiles()
    unknown=set(selected)-set(available)
    if unknown:
        raise RuntimeError(tr('Agentkällor saknas: ','Agent sources missing: ')+', '.join(sorted(unknown)))
    for name in selected:
        write_text(project/'.opencode/agents'/(name+'.md'),available[name].read_text(encoding='utf-8'))
    for name in ('TEAM_RULES.md','WORKFLOW.md','HANDOFF_TEMPLATE.md'):
        write_text(project/'.opencode/team'/name,(ROOT/name).read_text(encoding='utf-8'))


def clear_managed_step_limits(agents, selected):
    # Old inline overrides can reinstate caps even after Markdown is refreshed.
    for name in selected:
        if isinstance(agents.get(name),dict):
            agents[name].pop('steps',None)
            agents[name].pop('maxSteps',None)  # legacy OpenCode spelling


def refresh_team(project):
    """Refresh an installed team's behavior, preserving owner-selected controls."""
    project=require_local_project(project)
    manifest=read_manifest(project)
    selected=manifest.get('installed_agents',[])
    if not selected:
        raise RuntimeError(tr('Inget installerat team. Kör install först.','No installed team. Run install first.'))
    if not isinstance(selected,list) or any(not isinstance(n,str) for n in selected):
        raise RuntimeError(tr('Ogiltig agentlista i manifestet','Invalid manifest agent list'))
    cfg=json_load(project/'opencode.json')
    agents=cfg.get('agent',{})
    if not isinstance(agents,dict):
        raise RuntimeError(tr('opencode.json agent måste vara ett objekt','opencode.json agent must be an object'))
    # Preflight before updating files; retain unavailable custom agents untouched.
    unknown=set(selected)-set(profiles())
    if unknown:
        raise RuntimeError(tr('Agentkällor saknas: ','Agent sources missing: ')+', '.join(sorted(unknown)))
    clear_managed_step_limits(agents,selected)
    sync_team_files(project,selected)
    update_agents_md(project,selected,manifest.get('mode','PRIVATE'))
    write_json(project/'opencode.json',cfg)
    write_json(project/MANIFEST,{**manifest,'version':VERSION,'workflow_revision':2})
    say(tr('Teamets profiler och arbetsregler uppdaterade. Modellval, behörigheter och access-policy bevarade. Starta om OpenCode.',
           'Team profiles and workflow refreshed. Models, permissions and access policy preserved. Restart OpenCode.'))


def apply(project, selected, models, perm, mode, approved_remote=None, access=None):
    project=require_local_project(project)
    if not project.is_dir(): raise RuntimeError(tr('Projektkatalogen finns inte','Project directory does not exist'))
    existing=json_load(project/'opencode.json')
    if access is None:
        access=load_policy(project/ACCESS_FILE) if (project/ACCESS_FILE).exists() else default_access_policy(project,perm)
    validate(access)
    if Path(access['project_root']).resolve()!=project.resolve():
        raise RuntimeError(tr('Åtkomstpolicyn tillhör ett annat projekt; ändra project_root efter flytt.','Access policy belongs to another project; update project_root after moving it.'))
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
    sync_team_files(project,selected)
    cfg=existing
    cfg.setdefault('$schema','https://opencode.ai/config.json')
    a=cfg.get('agent') or {}
    if not isinstance(a,dict): raise RuntimeError(tr('opencode.json agent måste vara ett objekt','opencode.json agent must be an object'))
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
    clear_managed_step_limits(a,selected)
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
    if not isinstance(instructions,list):raise RuntimeError(tr('opencode.json instructions måste vara en lista','opencode.json instructions must be a list'))
    if ACCESS_RULES not in instructions:instructions.append(ACCESS_RULES)
    cfg['instructions']=instructions
    provider_ids=sorted({m.split('/')[0] for m in models.values() if m})
    if provider_ids:
        cfg['enabled_providers']=provider_ids
    write_json(project/'opencode.json',cfg)
    write_json(project/ACCESS_FILE,access)
    write_text(project/ACCESS_RULES,render_access_rules(access))
    (project/'.opencode/tools').mkdir(parents=True,exist_ok=True)
    write_text(project/'.opencode/tools/access_check.py',(ROOT/'access_check.py').read_text(encoding='utf-8'))
    write_text(project/'.opencode/tools/access_fetch.py',(ROOT/'access_fetch.py').read_text(encoding='utf-8'))
    update_agents_md(project,selected,mode)
    remote=approved_remote if approved_remote is not None else manifest.get('approved_remote')
    info={'version':VERSION,'workflow_revision':2,'installed_agents':selected,'models':models,'mode':mode,
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
       '- Git: integration coordinated by orchestrator; commit/push only with explicit authorization and according to policy.\n'
       '- A confidential project requires verified local inference and OS isolation where appropriate.\n'
       '- Routine implementation, bug fixes and regression checks are autonomous within approved scope.\n'
       '- Substantial redesign, changed product direction, new cost commitments and exceeded explicit budgets require user authorization (see team decision table).\n'
       '- Continue feasible authorized work after checkpoints; isolate blockers and keep compact active memory.\n')
    write_text(project/'PROJECT_POLICY.md',policy)
    say(tr('\nKlart: {count} agenter installerade i {project}.','\nDone: {count} agents installed in {project}.').format(count=len(selected),project=project))
    say(tr('Projektets konfiguration och tidigare filer har säkerhetskopierats vid ändring.','Project configuration and previous files were backed up when changed.'))
    say(tr('OBS: eventuella .opencode/agent-filer/andra överordnade globala regler kontrolleras separat av OpenCode.','NOTE: any .opencode/agent files or other overriding global rules are handled separately by OpenCode.'))
    say(tr('Starta om OpenCode för att läsa in de nya profilerna och reglerna.','Restart OpenCode to load the new profiles and rules.'))

def configure(project, mode='full'):
    project=require_local_project(project)
    if not project.exists():
        if confirm(tr('Skapa projektkatalog {project}?','Create project directory {project}?').format(project=project),False): project.mkdir(parents=True)
        else: raise RuntimeError(tr('Projektet finns inte','Project does not exist'))
    git=project/'.git'
    if not git.exists() and mode=='full':
        if confirm(tr('Projektet saknar Git-repo. Initiera med git init?','Project has no Git repository. Initialize with git init?'),True):
            subprocess.run(['git','init',str(project)],check=True)
    manifest=read_manifest(project)
    old=manifest.get('installed_agents',[])
    available=profiles()
    selected=select_agents(available,old) if mode in ('full','agents') else list(old)
    if not selected: raise RuntimeError(tr('Projektet saknar ett registrerat team. Välj Installera först.','Project has no registered team. Choose Install first.'))
    cfg=json_load(project/'opencode.json')
    oldmodels={n:(cfg.get('agent',{}).get(n,{}) or {}).get('model') for n in selected}
    existing_models=manifest.get('models',{})
    oldmodels={n:(oldmodels.get(n) or existing_models.get(n)) for n in selected}
    models=oldmodels
    if mode in ('full','models','agents'):
        if not confirm(tr('Kör opencode models och välj modell för varje vald agent?','Run opencode models and choose a model for each selected agent?'),True):
            raise RuntimeError(tr('Modellval krävs för nya installationer. Avbrutet.','Model selection is required for new installations. Cancelled.'))
        say(tr('OpenCode kan hämta katalogen över nätverket. Enbart denna begäran om modellista görs av verktyget.','OpenCode may fetch the catalog over the network. This tool makes only this model-list request.'))
        if not confirm(tr('Tillåt opencode models nu?','Allow opencode models now?'),True): raise RuntimeError(tr('Modellista ej godkänd','Model list not approved'))
        models=assign_models(selected,list_models(project),oldmodels)
    if mode in ('full','permissions'):
        classif=choose_mode() if mode=='full' else manifest.get('mode','PRIVATE')
        perms=permission_wizard(manifest.get('permissions'))
    else:
        classif=manifest.get('mode','PRIVATE')
        perms=manifest.get('permissions') or permission_wizard()
    if classif=='PRIVATE':
        say(tr('PRIVATE: verktyget kan inte bevisa att valda modeller körs lokalt.','PRIVATE: this tool cannot prove that selected models run locally.'))
        if mode in ('models','agents') and not confirm(tr('Bekräftar du att samtliga nu valda modeller verkligen körs lokalt och inte skickar data till molnet?','Do you confirm that all currently selected models run locally and do not send data to the cloud?'),False):
            raise RuntimeError(tr('Modelländringen i PRIVATE avbruten','PRIVATE model change cancelled'))
    access=load_policy(project/ACCESS_FILE) if (project/ACCESS_FILE).exists() else default_access_policy(project,perms)
    if mode in ('full','permissions') and confirm(tr('Redigera whitelist/blacklist för kataloger och internet nu?','Edit directory and internet allowlists/denylists now?'),False):
        access=access_wizard(project,access)
    say(tr('\n=== Sammanfattning ===','\n=== Summary ==='))
    say(tr('Projekt: {project}; Agenter: {count}; Sekretess: {mode}; Shell: {shell}; Push: {push}; Internet: {internet}','Project: {project}; Agents: {count}; Classification: {mode}; Shell: {shell}; Push: {push}; Internet: {internet}').format(project=project,count=len(selected),mode=classif,shell=action_label(perms['shell']),push=action_label(perms['gitpush']),internet=action_label(perms['internet'])))
    for n in selected: say(f'  {n:27} {models.get(n) or tr("ÄRV", "INHERIT")}')
    if not confirm(tr('Spara projektkonfiguration och profiler?','Save project configuration and profiles?'),False): return
    apply(project,selected,models,perms,classif,access=access)

def sync_access(project):
    project=require_local_project(project)
    if not read_manifest(project):raise RuntimeError(tr('Installera agentteamet i projektet först.','Install the agent team in the project first.'))
    access=load_policy(project/ACCESS_FILE)
    if Path(access['project_root']).resolve()!=project.resolve():
        raise RuntimeError(tr('project_root i policyn överensstämmer inte med projektkatalogen','Policy project_root does not match the project directory'))
    cfg=json_load(project/'opencode.json')
    manifest=read_manifest(project)
    cfg['permission']=make_permission({**manifest.get('permissions',{}),'_selected_agents':manifest.get('installed_agents',[])},access)
    ins=cfg.get('instructions',[])
    if not isinstance(ins,list):raise RuntimeError(tr('instructions måste vara en lista','instructions must be a list'))
    if ACCESS_RULES not in ins:ins.append(ACCESS_RULES)
    cfg['instructions']=ins
    write_text(project/ACCESS_RULES,render_access_rules(access))
    (project/'.opencode/tools').mkdir(parents=True,exist_ok=True)
    write_text(project/'.opencode/tools/access_check.py',(ROOT/'access_check.py').read_text(encoding='utf-8'))
    write_text(project/'.opencode/tools/access_fetch.py',(ROOT/'access_fetch.py').read_text(encoding='utf-8'))
    write_json(project/'opencode.json',cfg)
    say(tr('Policy synkroniserad. Starta om OpenCode för att läsa in nya regler.','Policy synchronized. Restart OpenCode to load the new rules.'))


def configure_access(project):
    project=require_local_project(project)
    manifest=read_manifest(project)
    if not manifest:raise RuntimeError(tr('Installera agentteamet i projektet först.','Install the agent team in the project first.'))
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
    say(tr('Åtkomstpolicyn är uppdaterad. Starta om OpenCode för att ladda nya instruktioner och behörigheter.','Access policy updated. Restart OpenCode to load new instructions and permissions.'))


def create_agent():
    say(tr('\n=== Skapa ny återanvändbar agentprofil ===','\n=== Create a reusable agent profile ==='))
    slug=prompt(tr('Agentnamn (ex. mechanical-engineer)','Agent name (e.g. mechanical-engineer)'))
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,54}',slug):
        raise RuntimeError(tr('Namnet måste vara gemener, siffror eller bindestreck och minst 3 tecken.','Name must start with a lowercase letter, use lowercase letters, digits or hyphens, and be 3–55 characters.'))
    if (PROFILES/(slug+'.md')).exists() or (CUSTOM/(slug+'.md')).exists():
        raise RuntimeError(tr('Agenten finns redan. Redigera dess fil manuellt i custom-profiles.','Agent already exists. Edit its file manually in custom-profiles.'))
    desc=prompt(tr('Beskrivning (på engelska)','Description (in English)'))
    if not desc: raise RuntimeError(tr('Beskrivning krävs','Description is required'))
    say(tr('Skriv instruktioner på engelska, avsluta med en ensam punkt på en rad.','Write instructions in English; finish with a single dot on a line.'))
    lines=[]
    while True:
        line=input()
        if line.strip()=='.': break
        lines.append(line)
    if not lines: raise RuntimeError(tr('Agentinstruktioner krävs','Agent instructions are required'))
    CUSTOM.mkdir(parents=True,exist_ok=True)
    profile=(f'---\ndescription: {json.dumps(desc,ensure_ascii=False)}\nmode: subagent\n---\n\n'
      '# '+slug+'\n\n'+'\n'.join(lines)+'\n\n'
      'Follow the project-wide team rules. Admit uncertainty, request suitable expertise, and keep handoffs concise.\n')
    write_text(CUSTOM/(slug+'.md'),profile)
    say(tr('Agenten sparad centralt: {path}','Agent saved centrally: {path}').format(path=CUSTOM/(slug+'.md')))
    say(tr('Välj nu Installera/Uppdatera i projektet för att inkludera den och välja en modell.','Now choose Install/Update in the project to include it and select a model.'))

def status(project):
    info=read_manifest(project)
    if not info:
        say(tr('Ingen v2-manifest hittad. Använd Installera för att migrera ett äldre projekt.','No v2 manifest found. Use Install to migrate an older project.')); return
    say(tr('Åtkomstpolicy: {path} (INTE en sandbox)','Access policy: {path} (NOT a sandbox)').format(path=project/ACCESS_FILE))
    say(tr('Projekt: {project}\nInstallerat: {version}\nKlassning: {mode}\nAgenter ({count}):','Project: {project}\nInstalled: {version}\nClassification: {mode}\nAgents ({count}):').format(project=project,version=info.get('version'),mode=info.get('mode'),count=len(info.get('installed_agents',[]))))
    for n in info.get('installed_agents',[]):
        say(f'  {n:27} {info.get("models",{}).get(n) or tr("ärv", "inherit")}')
    v=info.get('permissions',{})
    labels = [('shell',tr('shell','shell')),('file_edit',tr('filredigering','file editing')),
              ('gitpush',tr('git push','git push')),('internet',tr('internet','internet')),
              ('outside_read',tr('läsa utanför','outside read')),('outside_write',tr('skriva utanför','outside write')),
              ('sudo',tr('privilegierat','privileged')),('destructive',tr('destruktivt','destructive')),
              ('secrets',tr('hemligheter','secrets')),('mcp','MCP'),('packages',tr('paket','packages')),
              ('hardware',tr('hårdvara','hardware')),('unattended',tr('obevakat','unattended'))]
    for name,label in labels:
        say(f'  {label:15}: {action_label(v.get(name))}')

def run_opencode(project, resume=False):
    info=read_manifest(project)
    args=[]
    if resume: args.append('--continue')
    if info.get('permissions',{}).get('unattended'):
        say(tr('VARNING: --auto godkänner ASK-regler. Uttryckliga DENY gäller fortfarande; shell är inte sandbox.','WARNING: --auto approves ASK rules. Explicit DENY still applies; shell is not a sandbox.'))
        args.append('--auto')
    cmd=opencode_command(args)
    say(tr('Startar: ','Starting: ')+(cmd if isinstance(cmd,str) else ' '.join(cmd)))
    return subprocess.run(cmd,cwd=project).returncode

def menu():
    while True:
        say('\n=== agents-opencode v'+VERSION+' ===')
        say(tr(' 1) Installera / konfigurera ett projekt (välj agenter + modeller + behörigheter)',' 1) Install / configure a project (choose agents + models + permissions)'))
        say(tr(' 2) Ändra alla agentmodeller från hela opencode models-listan',' 2) Change all agent models using the full opencode models list'))
        say(tr(' 3) Välj / ta bort agenter i projektet',' 3) Select / remove project agents'))
        say(tr(' 4) Ändra projektets behörighetsguide',' 4) Change project permissions'))
        say(tr(' 5) Visa projektstatus',' 5) Show project status'))
        say(tr(' 6) Skapa en ny agentprofil (återanvändbar)',' 6) Create a reusable agent profile'))
        say(tr(' 7) Starta OpenCode',' 7) Start OpenCode'))
        say(tr(' 8) Fortsätt senaste OpenCode-session',' 8) Resume latest OpenCode session'))
        say(tr(' 9) Lista tillgängliga modeller',' 9) List available models'))
        say(tr('10) Redigera fil- och nätverkslistor (whitelist/blacklist)','10) Edit file and network allowlists/denylists'))
        say(tr('11) Synkronisera manuellt redigerad access-policy','11) Synchronize manually edited access policy'))
        say(tr('12) Uppdatera teamets profiler och arbetsregler (behåll projektval)','12) Refresh team profiles and workflow (preserve project choices)'))
        say(tr(' 0) Avsluta',' 0) Exit'))
        n=prompt(tr('Välj','Choose'),'0')
        if n=='0': return
        try:
            if n=='6': create_agent(); continue
            project=project_dir()
            if n=='1': configure(project,'full')
            elif n=='2': configure(project,'models')
            elif n=='3': configure(project,'agents')
            elif n=='4': configure(project,'permissions')
            elif n=='5': status(project)
            elif n=='7': return run_opencode(project)
            elif n=='8': return run_opencode(project,True)
            elif n=='10':configure_access(project)
            elif n=='11':sync_access(project)
            elif n=='12':refresh_team(project)
            elif n=='9':
                if confirm(tr('Tillåt opencode models (kan kontakta modellkatalogen)?','Allow opencode models (may contact the model catalog)?'),False):
                    for m in list_models(project): say(m)
            else: say(tr('Ogiltigt val.','Invalid choice.'))
        except (RuntimeError,ValueError,OSError,EOFError,KeyboardInterrupt,subprocess.SubprocessError) as e:
            say(tr('\nFel/avbrutet: ','\nError/cancelled: ')+str(e))

def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    # --lang is global, including after a command/project. No language prompt
    # for help/version, even if attached to an otherwise interactive command.
    set_language('en')
    explicit=None
    positional=[]
    i=0
    while i<len(args):
        arg=args[i]
        if arg=='--lang' or arg.startswith('--lang='):
            if arg=='--lang':
                i+=1
                if i==len(args): raise RuntimeError('--lang requires sv or en / --lang kräver sv eller en')
                lang=args[i]
            else: lang=arg.split('=',1)[1]
            set_language(lang)
            explicit=lang
        else: positional.append(arg)
        i+=1
    args=positional
    if any(a in ('--help','help','-h') for a in args):
        say('agents-opencode [--lang sv|en] [install|refresh|models-all|agents|permissions|access|sync-access|status|add-agent|run|resume|list-models] [PROJECT_PATH]')
        say(tr('Installation: python install.py (användarnivå). Ingen modell är förvald.','Installation: python install.py (user-level). No model is preselected.'))
        say(tr('--lang sv|en kan placeras före eller efter kommandot. Utan flaggan väljs språk vid interaktiv start; annars används engelska.','--lang sv|en may appear before or after the command. Without it, interactive startup asks for a language; otherwise English is used.'))
        return 0
    if any(a in ('--version','-V') for a in args): say(VERSION); return 0
    select_language(explicit)
    if not args: return menu()
    cmd=args[0]
    if len(args)>2: raise RuntimeError(tr('För många argument. agents-opencode --help','Too many arguments. agents-opencode --help'))
    if cmd=='add-agent': create_agent(); return
    project=Path(args[1]).expanduser().resolve() if len(args)>1 else Path.cwd().resolve()
    if cmd in ('install','init'): configure(project,'full')
    elif cmd=='refresh': refresh_team(project)
    elif cmd in ('models-all','models'): configure(project,'models')
    elif cmd=='agents': configure(project,'agents')
    elif cmd=='permissions': configure(project,'permissions')
    elif cmd=='access': configure_access(project)
    elif cmd=='sync-access': sync_access(project)
    elif cmd=='status': status(project)
    elif cmd=='run': return run_opencode(project)
    elif cmd=='resume': return run_opencode(project,True)
    elif cmd=='list-models':
        if confirm(tr('Tillåt opencode models (kan kontakta modellkatalogen)?','Allow opencode models (may contact the model catalog)?'),False):
            for x in list_models(project): say(x)
    else: raise RuntimeError(tr('Okänt kommando. agents-opencode --help','Unknown command. agents-opencode --help'))

if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,ValueError,OSError,subprocess.SubprocessError,KeyboardInterrupt,EOFError) as ex:
        print(tr('FEL: ','ERROR: ')+str(ex),file=sys.stderr); sys.exit(1)
