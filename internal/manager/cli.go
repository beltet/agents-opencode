package manager

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

type UI struct {
	In   *bufio.Reader
	Out  io.Writer
	Lang string
}

func NewUI(in io.Reader, out io.Writer, lang string) *UI {
	return &UI{In: bufio.NewReader(in), Out: out, Lang: lang}
}
func (u *UI) ask(label, def string) string {
	if def != "" {
		fmt.Fprintf(u.Out, "%s [%s]: ", label, def)
	} else {
		fmt.Fprintf(u.Out, "%s: ", label)
	}
	s, err := u.In.ReadString('\n')
	if err != nil && len(s) == 0 {
		return def
	}
	s = strings.TrimSpace(s)
	if s == "" {
		return def
	}
	return s
}
func (u *UI) yes(label string) bool  { return strings.EqualFold(u.ask(label+" (y/N)", "n"), "y") }
func (u *UI) say(s string, a ...any) { fmt.Fprintf(u.Out, s+"\n", a...) }
func (u *UI) choose(label string, allowed []string, def string) string {
	for {
		s := u.ask(label+" ["+strings.Join(allowed, "/")+" ]", def)
		for _, x := range allowed {
			if s == x {
				return s
			}
		}
		u.say("Invalid choice.")
	}
}
func (u *UI) action(label, def string) string {
	return u.choose(label, []string{"allow", "ask", "deny"}, def)
}
func (u *UI) fieldList(label string) []string {
	s := u.ask(label+" (comma-separated; blank=none)", "")
	out := []string{}
	for _, v := range strings.Split(s, ",") {
		v = strings.TrimSpace(v)
		if v != "" {
			out = append(out, v)
		}
	}
	return out
}
func (u *UI) catalogSelect(root string, c *Config) error {
	catalog, err := Catalog()
	if err != nil {
		return err
	}
	u.say("Available bundled roles:")
	for i, n := range catalog {
		flag := ""
		if contains(c.Agents, n) {
			flag = "*"
		}
		u.say("%2d %s %s", i+1, n, flag)
	}
	u.say("Enter agent numbers separated by commas, ranges (1-3), role names; or 'all'.")
	s := u.ask("Selection (blank retains current)", "")
	if s == "" {
		return nil
	}
	if s == "all" {
		c.Agents = append([]string(nil), catalog...)
		return nil
	}
	out := []string{}
	seen := map[string]bool{}
	for _, p := range strings.Split(s, ",") {
		p = strings.TrimSpace(p)
		name := ""
		if strings.Contains(p, "-") {
			parts := strings.SplitN(p, "-", 2)
			a, err1 := strconv.Atoi(strings.TrimSpace(parts[0]))
			b, err2 := strconv.Atoi(strings.TrimSpace(parts[1]))
			if err1 == nil && err2 == nil && a >= 1 && b <= len(catalog) && a <= b {
				for i := a; i <= b; i++ {
					n := catalog[i-1]
					if !seen[n] {
						seen[n] = true
						out = append(out, n)
					}
				}
				continue
			}
		}
		if n, err := strconv.Atoi(p); err == nil && n > 0 && n <= len(catalog) {
			name = catalog[n-1]
		} else if AvailableRole(p) {
			name = p
		} else if roleName.MatchString(p) {
			if _, err := os.Stat(filepath.Join(root, ".agents-opencode", "custom", p+".md")); err == nil {
				name = p
			}
		}
		if name == "" {
			return fmt.Errorf("unknown role %q; create .agents-opencode/custom/<role>.md first", p)
		}
		if !seen[name] {
			seen[name] = true
			out = append(out, name)
		}
	}
	if len(out) == 0 {
		return errors.New("no agents selected")
	}
	sort.Strings(out)
	c.Agents = out
	return nil
}
func listModels() ([]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "opencode", "models")
	b, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("opencode models: %w: %s", err, strings.TrimSpace(string(b)))
	}
	result := []string{}
	for _, line := range strings.Split(string(b), "\n") {
		line = strings.TrimSpace(line)
		if line != "" && !strings.ContainsAny(line, "\t ") {
			result = append(result, line)
		}
	}
	return result, nil
}
func (u *UI) assignModels(c *Config) error {
	if u.yes("Attempt to list available OpenCode model identifiers? May contact configured providers") {
		names, err := listModels()
		if err != nil {
			u.say("Model discovery unavailable: %v", err)
		} else {
			u.say("Discovered models (not proof of credentials/capabilities):")
			for _, n := range names {
				u.say("  %s", n)
			}
		}
	}
	if len(c.Models) == 0 {
		c.Models = map[string]string{}
	}
	bulk := u.ask("Model ID to assign to ALL selected agents (blank = individual/retain)", "")
	if bulk != "" {
		for _, a := range c.Agents {
			c.Models[a] = bulk
		}
	}
	for _, a := range c.Agents {
		m := u.ask("Model for "+a, c.Models[a])
		if m == "" {
			return fmt.Errorf("a model must be selected for %s", a)
		}
		c.Models[a] = m
	}
	return nil
}
func (u *UI) brief(root string) {
	path := filepath.Join(root, "PROJECT_BRIEF.md")
	if content, err := os.ReadFile(path); err == nil && !strings.Contains(string(content), "Describe what you want to build, constraints, expected features") {
		u.say("Existing brief preserved: %s (edit with your preferred editor)", path)
		return
	}
	u.say("Describe the project. You can expand PROJECT_BRIEF.md later.")
	text := u.ask("One-line project summary", "")
	if text != "" {
		_ = writeAtomic(path, []byte("# Project brief\n\n"+text+"\n"))
	}
}
func (u *UI) permissions(c *Config) {
	u.say("PERMISSIONS: OpenCode tool gates are not a firewall, device sandbox, or Git remote enforcement.")
	for _, name := range []string{"read", "edit", "bash", "webfetch", "websearch", "external_directory"} {
		c.Policy.Tools[name] = u.action("Tool "+name, c.Policy.Tools[name])
	}
	for _, name := range []string{"fetch", "pull", "commit", "push", "merge", "force_push", "destructive"} {
		c.Policy.Git[name] = u.action("Git "+name, c.Policy.Git[name])
	}
	c.Policy.Network.Internet = u.action("Internet policy intent", c.Policy.Network.Internet)
	if u.yes("Edit network allow/deny lists?") {
		c.Policy.Network.Allow = u.fieldList("Allowed hosts/URLs")
		c.Policy.Network.Deny = u.fieldList("Blocked hosts/URLs")
	}
	if u.yes("Add path or network share rule?") {
		for {
			path := u.ask("Absolute path (blank ends)", "")
			if path == "" {
				break
			}
			kind := u.choose("Type", []string{"local", "network-share"}, "local")
			rd := u.action("Read", "ask")
			wr := u.action("Write", "deny")
			c.Policy.Paths = append(c.Policy.Paths, PathRule{Path: path, Kind: kind, Read: rd, Write: wr})
		}
	}
	if u.yes("Add USB/serial/firmware rule?") {
		for {
			id := u.ask("Device identifier (VID:PID/serial/path; blank ends)", "")
			if id == "" {
				break
			}
			a := u.action("Hardware access", "ask")
			f := u.action("Firmware flashing", "deny")
			c.Policy.Devices = append(c.Policy.Devices, DeviceRule{Identifier: id, Access: a, Flash: f})
		}
	}
	if u.yes("Configure per-agent tool overrides?") {
		for {
			agent := u.ask("Agent (blank ends)", "")
			if agent == "" {
				break
			}
			if !contains(c.Agents, agent) {
				u.say("Not installed: %s", agent)
				continue
			}
			tool := u.choose("Tool", []string{"read", "edit", "bash", "webfetch", "websearch", "external_directory"}, "bash")
			if c.Policy.AgentOverrides == nil {
				c.Policy.AgentOverrides = map[string]map[string]string{}
			}
			if c.Policy.AgentOverrides[agent] == nil {
				c.Policy.AgentOverrides[agent] = map[string]string{}
			}
			c.Policy.AgentOverrides[agent][tool] = u.action("Action", "ask")
		}
	}
	c.Policy.Unattended = u.yes("Enable unattended mode (--auto)? WARNING: ASK may be auto-approved")
}
func (u *UI) gitConfig(c *Config) {
	c.Git.Mode = u.choose("Git mode", []string{"local", "existing", "remote"}, c.Git.Mode)
	c.Git.AuthorName = u.ask("Commit author name", c.Git.AuthorName)
	c.Git.AuthorEmail = u.ask("Commit author email", c.Git.AuthorEmail)
	c.Git.Branch = u.ask("Default branch (documentation only)", c.Git.Branch)
	if c.Git.Mode == "remote" {
		c.Git.Remote = u.ask("Remote name", c.Git.Remote)
		c.Git.URL = u.ask("Remote URL (use ssh://user@host:port/group/repo.git for custom port)", c.Git.URL)
		c.Git.SSHHost = u.ask("SSH host (metadata)", c.Git.SSHHost)
		pn := u.ask("SSH port", strconv.Itoa(c.Git.SSHPort))
		if x, err := strconv.Atoi(pn); err == nil {
			c.Git.SSHPort = x
		}
		c.Git.SSHUser = u.ask("SSH username (not commit author)", c.Git.SSHUser)
		c.Git.SSHIdentity = u.ask("Existing SSH identity path (never copy key)", c.Git.SSHIdentity)
	}
	u.say("Git config recorded; no remote/identity will be changed until 'agents-opencode git-apply'.")
}
func (u *UI) setup(root string, existing bool, dry bool) error {
	if err := checkOpenCodeCompatibility(); err != nil {
		return err
	}
	c := Default()
	if existing {
		loaded, err := Load(root)
		if err != nil {
			return err
		}
		c = loaded
	}
	if !existing {
		u.say("New project configuration: choose roles and models. No automatic selection or model recommendation.")
	}
	if err := u.catalogSelect(root, &c); err != nil {
		return err
	}
	if err := u.assignModels(&c); err != nil {
		return err
	}
	if u.yes("Configure permissions now?") {
		u.permissions(&c)
	}
	if u.yes("Configure Git settings now?") {
		u.gitConfig(&c)
	}
	if err := c.Validate(); err != nil {
		return err
	}
	changes, _, err := Apply(root, c, true)
	if err != nil {
		return err
	}
	u.say("Preview: %d files to create/update:", len(changes))
	for _, p := range changes {
		u.say("  %s", p)
	}
	if !dry && !u.yes("Apply and back up existing files?") {
		u.say("Cancelled. No generated files changed.")
		return nil
	}
	if dry {
		u.say("Dry run completed. No files changed.")
		return nil
	}
	changes, backupDir, err := Apply(root, c, false)
	if err != nil {
		return err
	}
	u.say("Installed %d files. Backup: %s", len(changes), backupDir)
	u.brief(root)
	return nil
}
func gitApply(root string, c Config, u *UI) error {
	if c.Git.Mode == "local" {
		if _, err := os.Stat(filepath.Join(root, ".git")); os.IsNotExist(err) {
			u.say("No Git repository exists here. 'git init' will not contact a remote.")
			if u.yes("Initialize a local Git repository?") {
				cmd := exec.Command("git", "-C", root, "init")
				out, err := cmd.CombinedOutput()
				if err != nil {
					return fmt.Errorf("git init: %w: %s", err, out)
				}
			}
		}
		if _, err := os.Stat(filepath.Join(root, ".git")); os.IsNotExist(err) {
			return nil
		}
	}
	if _, err := os.Stat(filepath.Join(root, ".git")); err != nil {
		return fmt.Errorf("not a Git working tree: %w; initialize or clone separately", err)
	}
	// Only explicit user confirmation permits changing an existing repository.
	args := [][]string{}
	if c.Git.AuthorName != "" {
		args = append(args, []string{"config", "--local", "user.name", c.Git.AuthorName})
	}
	if c.Git.AuthorEmail != "" {
		args = append(args, []string{"config", "--local", "user.email", c.Git.AuthorEmail})
	}
	if c.Git.Mode == "remote" {
		cmd := exec.Command("git", "-C", root, "remote", "get-url", c.Git.Remote)
		old, err := cmd.Output()
		if err == nil && strings.TrimSpace(string(old)) != c.Git.URL {
			return fmt.Errorf("remote %s already exists with different URL (%s); refusing overwrite; change manually", c.Git.Remote, strings.TrimSpace(string(old)))
		}
		if err != nil {
			args = append(args, []string{"remote", "add", c.Git.Remote, c.Git.URL})
		}
	}
	for _, a := range args {
		u.say("  git %s", strings.Join(a, " "))
	}
	if !u.yes("Apply the Git changes shown above?") {
		return nil
	}
	for _, a := range args {
		cmd := exec.Command("git", append([]string{"-C", root}, a...)...)
		out, err := cmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("git %v: %w: %s", a, err, out)
		}
	}
	u.say("Git settings applied. SSH identity/path was NOT changed automatically.")
	return nil
}
func modelsCommand(u *UI, root string, dry bool) error {
	c, err := Load(root)
	if err != nil {
		return err
	}
	if err := u.assignModels(&c); err != nil {
		return err
	}
	return applyAndConfirm(u, root, c, dry)
}
func agentsCommand(u *UI, root string, dry bool) error {
	c, err := Load(root)
	if err != nil {
		return err
	}
	if err = u.catalogSelect(root, &c); err != nil {
		return err
	}
	if err := u.assignModels(&c); err != nil {
		return err
	}
	return applyAndConfirm(u, root, c, dry)
}
func applyAndConfirm(u *UI, root string, c Config, dry bool) error {
	changes, _, err := Apply(root, c, true)
	if err != nil {
		return err
	}
	u.say("Files affected (%d):", len(changes))
	for _, x := range changes {
		u.say("  " + x)
	}
	if dry {
		u.say("Dry run; no writes")
		return nil
	}
	if !u.yes("Apply changes? (existing files backed up)") {
		return nil
	}
	_, dir, err := Apply(root, c, false)
	if err == nil {
		u.say("Applied. Backups: %s", dir)
	}
	return err
}
func status(u *UI, root string) error {
	c, err := Load(root)
	if err != nil {
		return err
	}
	u.say("agents-opencode %s | project %s", Version, root)
	for _, a := range c.Agents {
		u.say("  %-26s %s", a, c.Models[a])
	}
	u.say("Git mode: %s, remote %s, URL %s", c.Git.Mode, c.Git.Remote, c.Git.URL)
	u.say("Unattended: %v; internet policy: %s", c.Policy.Unattended, c.Policy.Network.Internet)
	return nil
}
func doctor(u *UI, root string) error {
	c, err := Load(root)
	if err != nil {
		return err
	}
	u.say("Configuration format and assignments: OK")
	if _, err := exec.LookPath("opencode"); err != nil {
		u.say("WARNING: opencode not found on PATH")
	} else {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		out, err := exec.CommandContext(ctx, "opencode", "--version").CombinedOutput()
		if err != nil {
			u.say("WARNING: cannot determine OpenCode version: %s", out)
		} else {
			u.say("OpenCode reported version: %s", strings.TrimSpace(string(out)))
		}
	}
	for _, a := range c.Agents {
		if _, err := os.Stat(filepath.Join(root, ".opencode", "agents", a+".md")); err != nil {
			u.say("WARNING: missing generated profile %s", a)
		}
	}
	if c.Policy.Unattended {
		u.say("WARNING: unattended mode auto-approves ASK decisions. Ensure dangerous commands are DENY.")
	}
	if len(c.Policy.Network.Allow)+len(c.Policy.Network.Deny) > 0 {
		u.say("WARNING: URL allow/deny lists are advisory; not an enforced network firewall.")
	}
	if len(c.Policy.Devices) > 0 {
		u.say("WARNING: hardware/USB/firmware rules are advisory; use OS isolation for actual enforcement.")
	}
	if c.Policy.Git["push"] == "allow" {
		u.say("WARNING: shell-level Git push rules cannot guarantee remote/branch confinement.")
	}
	u.say("WARNING: effective global/parent OpenCode configuration may override generated settings; inspect with OpenCode debug commands.")
	return nil
}
func runOpenCode(root string, c Config, resume bool) error {
	if err := checkOpenCodeCompatibility(); err != nil {
		return err
	}
	if _, err := exec.LookPath("opencode"); err != nil {
		return fmt.Errorf("opencode executable not found: %w", err)
	}
	args := []string{}
	if resume {
		args = append(args, "--continue")
	}
	if contains(c.Agents, "orchestrator") {
		args = append(args, "--agent", "orchestrator")
	}
	if c.Policy.Unattended {
		args = append(args, "--auto")
	}
	cmd := exec.Command("opencode", args...)
	cmd.Dir = root
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
func migrateLegacy(u *UI, root string, dry bool) error {
	manifest := filepath.Join(root, ".opencode", "agentteam-manifest.json")
	b, err := os.ReadFile(manifest)
	if err != nil {
		return fmt.Errorf("legacy manifest not found: %w", err)
	}
	var old struct {
		Agents []string          `json:"installed_agents"`
		Models map[string]string `json:"models"`
	}
	if err = json.Unmarshal(b, &old); err != nil {
		return err
	}
	if len(old.Agents) == 0 {
		return errors.New("legacy manifest has no agents")
	}
	c := Default()
	c.Agents = old.Agents
	c.Models = old.Models
	u.say("Legacy migration: %d roles, selected models imported; permissions reset to conservative defaults. Check before confirming.", len(c.Agents))
	for _, a := range c.Agents {
		u.say("  %s -> %s", a, c.Models[a])
		if c.Models[a] == "" {
			c.Models[a] = u.ask("Missing model for "+a, "")
		}
	}
	return applyAndConfirm(u, root, c, dry)
}
func backupCommand(u *UI, root string) error {
	paths := []string{configFile, "opencode.json", "AGENTS.md", "PROJECT_BRIEF.md", "AGENT_ACCESS_POLICY.json", ".agents-opencode/TEAM_REGISTRY.md"}
	c, err := Load(root)
	if err != nil {
		return err
	}
	for _, a := range c.Agents {
		paths = append(paths, ".opencode/agents/"+a+".md")
	}
	for _, name := range []string{"TEAM_RULES.md", "WORKFLOW.md", "HANDOFF_TEMPLATE.md", "ACCESS_RULES.md"} {
		paths = append(paths, ".opencode/team/"+name)
	}
	dest, err := backup(root, paths)
	if err == nil {
		u.say("Backup created at %s", dest)
	}
	return err
}
func restoreCommand(u *UI, root string, source string) error {
	if source == "" {
		return errors.New("restore needs --from=<backup_directory>")
	}
	base := filepath.Join(root, ".agents-opencode", "backups")
	abs, err := filepath.Abs(source)
	if err != nil {
		return err
	}
	rel, err := filepath.Rel(base, abs)
	if err != nil || rel == "." || strings.HasPrefix(rel, "..") || filepath.IsAbs(rel) {
		return errors.New("restore source must be a specific backup under .agents-opencode/backups")
	}
	files := map[string][]byte{}
	err = filepath.WalkDir(abs, func(path string, de os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if de.IsDir() {
			return nil
		}
		if !de.Type().IsRegular() {
			return fmt.Errorf("backup has nonregular file: %s", path)
		}
		rel, err := filepath.Rel(abs, path)
		if err != nil {
			return err
		}
		b, err := os.ReadFile(path)
		if err == nil {
			files[rel] = b
		}
		return err
	})
	if err != nil {
		return err
	}
	if len(files) == 0 {
		return errors.New("empty backup")
	}
	if err = CheckManagedPaths(root, files); err != nil {
		return err
	}
	u.say("Restore %d backed up files from %s (does not delete new files)", len(files), abs)
	if !u.yes("Confirm restore?") {
		return nil
	}
	paths := []string{}
	for path := range files {
		paths = append(paths, path)
	}
	if _, err = backup(root, paths); err != nil {
		return err
	}
	for path, data := range files {
		if err = writeAtomic(filepath.Join(root, path), data); err != nil {
			return err
		}
	}
	return nil
}
func Launch(args []string, in io.Reader, out io.Writer) error {
	cmd := ""
	project := "."
	lang := "sv"
	dry := false
	from := ""
	for _, a := range args {
		switch {
		case a == "--dry-run":
			dry = true
		case a == "--lang=en":
			lang = "en"
		case a == "--lang=sv":
			lang = "sv"
		case strings.HasPrefix(a, "--project="):
			project = strings.TrimPrefix(a, "--project=")
		case strings.HasPrefix(a, "--from="):
			from = strings.TrimPrefix(a, "--from=")
		case strings.HasPrefix(a, "--"):
			return fmt.Errorf("unknown flag %s", a)
		case cmd == "":
			cmd = a
		default:
			project = a
		}
	}
	u := NewUI(in, out, lang)
	if cmd == "version" {
		u.say(Version)
		return nil
	}
	if cmd == "catalog" {
		names, _ := Catalog()
		for _, name := range names {
			u.say(name)
		}
		return nil
	}
	if cmd == "list-models" {
		names, err := listModels()
		if err != nil {
			return err
		}
		for _, n := range names {
			u.say(n)
		}
		return nil
	}
	root, err := rootPath(project)
	if err != nil {
		return err
	}
	if cmd == "" {
		u.say("agents-opencode %s — %s", Version, root)
		u.say("1 install/configure | 2 agents | 3 models | 4 permissions | 5 git | 6 status | 7 doctor | 8 run | 9 refresh | 0 quit")
		pick := u.ask("Choice", "0")
		cmd = map[string]string{"1": "install", "2": "agents", "3": "models", "4": "permissions", "5": "git", "6": "status", "7": "doctor", "8": "run", "9": "refresh"}[pick]
		if cmd == "" {
			return nil
		}
	}
	_, e := os.Stat(ConfigPath(root))
	existing := e == nil
	switch cmd {
	case "install", "configure":
		return u.setup(root, existing, dry)
	case "agents":
		return agentsCommand(u, root, dry)
	case "models", "models-all":
		return modelsCommand(u, root, dry)
	case "permissions", "access", "hardware":
		c, err := Load(root)
		if err != nil {
			return err
		}
		u.permissions(&c)
		return applyAndConfirm(u, root, c, dry)
	case "git":
		c, err := Load(root)
		if err != nil {
			return err
		}
		u.gitConfig(&c)
		return applyAndConfirm(u, root, c, dry)
	case "git-apply":
		c, err := Load(root)
		if err != nil {
			return err
		}
		return gitApply(root, c, u)
	case "status":
		return status(u, root)
	case "doctor", "audit":
		return doctor(u, root)
	case "refresh":
		c, err := Load(root)
		if err != nil {
			return err
		}
		return applyAndConfirm(u, root, c, dry)
	case "backup":
		return backupCommand(u, root)
	case "restore":
		return restoreCommand(u, root, from)
	case "migrate":
		if existing {
			return errors.New("already configured; use refresh")
		}
		return migrateLegacy(u, root, dry)
	case "run", "resume":
		c, err := Load(root)
		if err != nil {
			return err
		}
		return runOpenCode(root, c, cmd == "resume")
	default:
		return fmt.Errorf("unknown command %q. Use install, agents, models, permissions, git, git-apply, status, doctor, refresh, backup, restore, migrate, run, resume, catalog, list-models, version", cmd)
	}
}

// The manager only emits the OpenCode 1.x shape known to be compatible with its tests.
// Missing OpenCode is allowed during offline configuration; 'run' checks separately.
func checkOpenCodeCompatibility() error {
	if _, err := exec.LookPath("opencode"); err != nil {
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 4*time.Second)
	defer cancel()
	b, err := exec.CommandContext(ctx, "opencode", "--version").CombinedOutput()
	if err != nil {
		return nil
	} // unknown version: doctor will report incomplete validation
	v := strings.TrimSpace(string(b))
	v = strings.TrimPrefix(v, "v")
	if strings.HasPrefix(v, "2.") || strings.HasPrefix(v, "3.") {
		return fmt.Errorf("OpenCode %s is not validated: this beta only generates tested 1.x configuration; refusing to overwrite project", v)
	}
	return nil
}
