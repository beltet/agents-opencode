# OpenCode Agentteam — Portable installer v2.1.0

**A portable engineering-agent team installer for OpenCode 1.x (designed for v1.19.5)**. The 23 included specialist profiles and working instructions are in English. The management wizard is in Swedish. Each colleague chooses their own models and project permissions; **no model IDs, API keys, providers or user-specific paths are preconfigured**.

## Requirements

- Linux (Fedora, CachyOS and most distributions); a Bash shell, Python 3 standard library and Git.
- The `opencode` executable and suitable model providers must be configured separately (`opencode models` should work).
- `unzip` to extract the archive. No root privileges or Python packages are needed for this installer.
- The package uses **OpenCode 1.x** `opencode.json` configuration syntax (`permission`, `bash`, `task`, `agent`). OpenCode v2 uses a different format; do not use these generated permissions with v2.

## Install or replace the old management tool

```bash
cd ~/Downloads
unzip OpenCode-Agentteam-Portable-v2.1.0.zip
cd OpenCode-Agentteam-Portable-v2.1.0
bash install.sh
```

- User command: `~/.local/bin/agents-opencode`.
- Central templates and Python logic: `${XDG_DATA_HOME:-~/.local/share}/agents-opencode/lib/`.
- Existing central installation of this same tool is replaced; custom agent profiles are migrated from its `custom-profiles/` directory, and the old central version is deleted after success.
- Existing **project repositories and user configurations are not deleted** by the system installer. When configuring an existing project, modified files are backed up beside themselves before replacement. The program never removes your global OpenCode credentials.
- If `agents-opencode` is not in PATH: for Fish use `fish_add_path -U ~/.local/bin`; for Bash add `$HOME/.local/bin` to PATH.

## New projects

```bash
mkdir -p ~/git/new-project && cd ~/git/new-project
agents-opencode
# Select 1 – Install / configure
```

The complete setup wizard will:

1. Ask which agents to install. Choose **all**, the suggested **core three**, or a comma/range list of agent numbers. The list is expandable with user-created roles.
2. Call the **installed OpenCode** program using `opencode models` **once** and show the **complete available model list separately for every selected agent**, without filtering or truncating it. Enter its number for each role. `p` reuses the previous assignment, `i` intentionally inherits the caller’s model; Enter preserves an existing assignment. There are no preset model selections. For `image-analyst`, pick a model that actually supports images.
3. Ask whether the project is PRIVATE, SHAREABLE or HYBRID. PRIVATE mode requires you to verify the selected endpoints really are local. The tool cannot determine whether an alias or proxy forwards data to the cloud.
4. Run the permission wizard. Choose a starting preset (locked computer, development machine, isolated VM), then override **every individual permission** with allow / ask / deny. Optionally enter mounted share directories with separate read/write choices. You can also open the new path/network allowlist wizard to configure exceptions.
5. Show a review of the exact agents, models, and main permissions and request confirmation **before writing any files**.

New projects may be initialized as Git repositories with an explicit prompt. You can install a smaller subset of roles, e.g. orchestrator, architect, programmer and documenter, rather than all 23.

## Menu and shortcuts

| Menu action | Command |
| --- | --- |
| Install / migrate / configure a project | `agents-opencode install` |
| Reassign all selected models, full model list for each | `agents-opencode models-all` |
| Add/remove installed roles in a project | `agents-opencode agents` |
| Edit the permission wizard | `agents-opencode permissions` |
| Edit path and network allowlists/denylists | `agents-opencode access` |
| Apply manual edits to access policy | `agents-opencode sync-access` |
| Show chosen agents/models/permissions | `agents-opencode status` |
| Create a reusable custom English agent | `agents-opencode add-agent` |
| Start OpenCode with this project's mode | `agents-opencode run` |
| Continue latest OpenCode session | `agents-opencode resume` |
| Show unfiltered available models | `agents-opencode list-models` |

All commands accept an optional `PROJECT_PATH` argument, e.g. `agents-opencode status ~/git/minroj`; in the menu you can enter a different path. Without an argument, shortcuts use the current directory.

## Permission wizard

You may select **allow** (no prompt), **ask** (interactive approval) or **deny** (block) for:

- Shell commands and file edits in OpenCode.
- Ordinary Git push commands (separately from other shell commands).
- Web search/fetch and typical network-related shell commands.
- Read versus write **outside the project worktree** with OpenCode file tools.
- Named mounted network share directories with read/write permissions independently.
- `sudo`, risky/destructive commands, credential/key access.
- MCP/external tools and services, package installation, hardware flashing/RF-capable tools.
- Unattended launch (`opencode --auto`). **In unattended mode, OpenCode auto-approves `ask`**; mark anything truly forbidden as `deny`.

**Security warning:** OpenCode permissions are *not* a firewall or filesystem sandbox. When Bash or allowed project code executes, it has the authority of the hosting OS account. Even when a command pattern for `curl`, Git or `rm` is denied, a Python program, Git hook, shell alias or build script can perform equivalent operations. **Per-address internet allowlists, forced access only to an exact Git remote, true split read/write access to mounted shares and no access outside the repo require OS controls** (isolated VM/container, permissions, restricted mounts, firewall/proxy). The wizard configures best-effort OpenCode tool permissions, not hardened isolation.

For an unattended VM, use an isolated nonprivileged system account, only mount designated files/shares, remove unnecessary credentials, apply network restrictions at the OS/virtual network layer, and budget provider usage separately. Avoid `--auto` on a sensitive workstation without isolation.


## v2.1: one editable access-policy file per project

**This is an AGENT BEHAVIOR POLICY and a best-effort mapping to OpenCode 1.x tools, not an operating-system access-control mechanism.** The agent receives the project-specific English rules through `opencode.json` `instructions`. Existing `AGENTS.md` is also extended with a managed reference. Other files can override or conflict with these instructions; review global and parent configurations separately.

At first install, the wizard writes `AGENT_ACCESS_POLICY.json` inside the repository. It is the authoritative editable document for path and hostname decisions. **Default outside access is deny** for locked/development presets, including root `/`; project worktree access follows your project edit permissions. Deliberately choosing a broad VM preset can override the outside defaults. An explicit `"path": "/"` allow rule is rejected; broad access must be chosen knowingly.

Here is a **sample** (use paths that really exist on your system; the wizard generates the project root and rest of the fields):

```json
{
  "version": 1,
  "advisory_only": true,
  "project_root": "/home/user/git/example",
  "filesystem": {
    "default_outside": {"read": "deny", "write": "deny"},
    "paths": [
      {"path": "/mnt/team-documents", "kind": "network-share", "read": "allow", "write": "deny"},
      {"path": "/home/user/reference", "kind": "local", "read": "allow", "write": "deny"},
      {"path": "/mnt/team-documents/confidential", "kind": "network-share", "read": "deny", "write": "deny"}
    ]
  },
  "network": {
    "default": "deny",
    "hosts": [
      {"scheme": "https", "host": "docs.python.org", "access": "allow"},
      {"scheme": "https", "host": "*.internal.example", "access": "allow"},
      {"scheme": "https", "host": "blocked.internal.example", "access": "deny"}
    ]
  }
}
```

Path decisions operate on canonicalized absolute paths, and more specific path rules override broader ones. Network rules use **hostnames, protocols and optional ports**, not unrestricted URL substrings. Explicit later host matches can veto wildcard matches. Configured AI model provider APIs and separately approved Git remotes are handled independently and are **not** intercepted by this network list. For SSH-based Git access, continue to use project-specific approved remotes rather than treating an SSH hostname as a universal network permission.

### Use the allowlist wizard or edit JSON manually

From the project directory:

```bash
agents-opencode access        # Interactive allow/deny for paths, shares and hostnames
# or edit AGENT_ACCESS_POLICY.json in your editor, then:
agents-opencode sync-access  # Validate and update OpenCode tool permissions and instruction files
```

Restart OpenCode after policy changes. A manual JSON edit without `sync-access` does **not** regenerate the agent instructions or native permissions.

### Optional policy checks and approved web documentation

```bash
python3 .opencode/tools/access_check.py path read /mnt/team-documents/readme.txt
python3 .opencode/tools/access_check.py path write /mnt/team-documents/readme.txt
python3 .opencode/tools/access_check.py url https://docs.python.org/3/
python3 .opencode/tools/access_fetch.py https://docs.python.org/3/
```

`access_check.py` returns 0 for ALLOW, 2 for ASK, and 3 for DENY. It never accesses the target; it is an advisory policy inspector. `access_fetch.py` runs a real read-only **GET** only when the hostname is explicitly allowed: it limits output to 2 MiB, has a short timeout, and refuses redirects. It does not allow arbitrary shell or network traffic on the host. Neither tool is a firewall or a security sandbox.

**OpenCode v1.x limitation:** `webfetch` can only be `allow/ask/deny`, without hostname-specific rules. When a hostname list is configured, the installer therefore blocks unrestricted `webfetch`/`websearch` and provides `access_fetch.py` for explicitly allowlisted GET requests instead. If normal `bash` is permitted, an agent or subprocess can still bypass these policy checks by using other programs. `read`/`edit`/`external_directory` rules are also best-effort OpenCode controls, not reliable isolation of mounts or secrets. `--auto` automatically approves `ask`; do not use it as a way to enforce an access-control boundary.

**If enforced allowlists are required**, configure restricted mounts/UIDs with container or VM isolation and use a firewall, DNS/proxy policies or equivalent egress rules. For example, don't mount private directories into an unattended VM. Do not store host credentials in the VM. Only grant it the network services and shares you want it to reach. Your cloud-model provider receives inference prompts outside the agent-initiated network allowlist; project data classification remains a separate control.

## Files written inside a project

```text
project/
  AGENTS.md                                # Existing content preserved; one managed section
  PROJECT_POLICY.md                        # Generated project-level summary (backed up)
  AGENT_ACCESS_POLICY.json                 # Declarative per-project allow/deny rules
  opencode.json                            # Models, provider allowlist and OpenCode permissions
  .opencode/
    agentteam-manifest.json                # Selection and permissions for later reconfiguration
    agents/<only selected role names>.md    # English role profiles
    team/TEAM_RULES.md
    team/WORKFLOW.md
    team/HANDOFF_TEMPLATE.md
    team/ACCESS_RULES.md                   # Generated English policy instructions, loaded by OpenCode
    tools/access_check.py                  # Advisory read/write/URL decision helper
    tools/access_fetch.py                  # Read-only HTTP GET for approved hosts
```

`opencode.json` is **merged with the existing JSON object**: unrelated settings, provider definitions and `small_model` are preserved; the chosen project-specific `model`, managed `agent.*.model`, `enabled_providers` and `permission` reflect this wizard. No models are hardcoded in the supplied agent Markdown files. Existing non-managed agent files are preserved. When an already managed role is deselected it is backed up and removed from the installed project.

The setup tool currently handles standard `opencode.json` JSON, not commented JSONC. For existing `opencode.jsonc`, migrate or merge manually first; do not assume this tool has covered all global/special OpenCode configuration sources.

## Migrating an earlier v1.x agentteam installation

1. Extract and install this manager with `bash install.sh`; it replaces the previous central manager, not your project.
2. Enter the existing repo (for example `cd ~/git/minroj`), run `agents-opencode install`, choose the **desired subset** and models, then review permissions.
3. The program detects known old team-agent files, backs up changed files, and replaces their old per-agent YAML permissions with centrally configured project permissions. Your existing unrelated JSON configuration and `AGENTS.md` content are kept. Known legacy managed instructions in `AGENTS.md` are replaced by the new managed block; nonstandard older text may need manual review.
4. Inspect `git diff -- AGENTS.md opencode.json` and `git status --short` before committing. Files from the **old project-local helper package** such as `.opencode/tools/git_sync.py` are deliberately not deleted because they may be in use; remove them manually after checking.

## Creating and sharing custom agents

Select **6 – Create a reusable agent**, or run `agents-opencode add-agent`. Give an agent slug, English description and multi-line prompt. End with a line containing only a period (`.`). Custom profiles live in `~/.local/share/agents-opencode/custom-profiles/` (or your `XDG_DATA_HOME`). They appear in future project agent-selection menus and survive reinstallation of the central manager. You can copy those `.md` files to another colleague's `custom-profiles/` folder, or include them in a separately distributed archive.

## Checking the installation

```bash
agents-opencode --version
agents-opencode status ~/git/my-project
cd ~/git/my-project
opencode agent list | grep -E 'orchestrator|system-architect|technical-documenter'
```

A custom role must be installed in a project before OpenCode can use it there. Model names and tool support depend on the local OpenCode installation; the installer cannot benchmark or validate whether a specific text model supports image inputs or reliable tool calling.

## Test status

The Python logic, path and hostname decision logic, and OpenCode config generation have been unit-tested locally with simulated model lists; the shell installer uses a portable user-level entry point. **Not yet end-to-end tested on your specific Fedora/OpenCode 1.19.5 installation.** No tests send code to model providers or modify your actual repositories.
