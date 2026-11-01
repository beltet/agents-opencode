package manager

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/beltet/agents-opencode/assets"
)

const begin = "<!-- agents-opencode:begin -->"
const end = "<!-- agents-opencode:end -->"

type orderedPermission struct {
	Base  string
	Rules [][2]string
}

func (p orderedPermission) MarshalJSON() ([]byte, error) {
	if p.Rules == nil {
		return json.Marshal(p.Base)
	}
	parts := []string{}
	for _, r := range p.Rules {
		k, _ := json.Marshal(r[0])
		v, _ := json.Marshal(r[1])
		parts = append(parts, string(k)+":"+string(v))
	}
	return []byte("{" + strings.Join(parts, ",") + "}"), nil
}
func mapRules(rules ...[2]string) orderedPermission { return orderedPermission{Rules: rules} }
func tool(c Config, name string) string {
	if v := c.Policy.Tools[name]; tri[v] {
		return v
	}
	return "ask"
}
func gitPermission(c Config, name string) string {
	if v := c.Policy.Git[name]; tri[v] {
		return v
	}
	return "deny"
}
func readOnlyRole(name string) bool {
	return name == "code-reviewer" || name == "image-analyst" || name == "system-architect" || name == "technical-educator"
}
func opencodeConfig(root string, c Config) ([]byte, error) {
	current := map[string]json.RawMessage{}
	old, err := os.ReadFile(filepath.Join(root, "opencode.json"))
	if err == nil {
		if err = json.Unmarshal(old, &current); err != nil {
			return nil, fmt.Errorf("existing opencode.json is not plain JSON: %w (edit/migrate manually; no overwrite)", err)
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	if raw := current["agent"]; len(raw) > 0 {
		existing := map[string]json.RawMessage{}
		if err = json.Unmarshal(raw, &existing); err != nil {
			return nil, fmt.Errorf("existing agent config invalid: %w", err)
		}
		// Existing custom agents remain untouched; remove only previously managed roles
		// that the user explicitly deselected during a confirmed configuration change.
		if prior, err := Load(root); err == nil {
			for _, oldRole := range prior.Agents {
				if !contains(c.Agents, oldRole) {
					delete(existing, oldRole)
				}
			}
		}
		for _, a := range c.Agents {
			rawModel, _ := pretty(agentConfig(c, a))
			existing[a] = rawModel
		}
		newAgents, _ := json.Marshal(existing)
		current["agent"] = newAgents
	} else {
		agents := map[string]any{}
		for _, a := range c.Agents {
			agents[a] = agentConfig(c, a)
		}
		b, _ := json.Marshal(agents)
		current["agent"] = b
	}
	// Avoid globally loosening an unrelated OpenCode configuration: tool defaults apply to managed agents only.
	schema, _ := json.Marshal("https://opencode.ai/config.json")
	if len(current["$schema"]) == 0 {
		current["$schema"] = schema
	}
	if contains(c.Agents, "orchestrator") {
		d, _ := json.Marshal("orchestrator")
		current["default_agent"] = d
	}
	// no arbitrary root-level permission edits; per-agent permissions are explicit.
	return pretty(current)
}
func agentConfig(c Config, name string) map[string]any {
	p := map[string]any{
		"read":     mapRules([2]string{"*", tool(c, "read")}, [2]string{"*.env", "ask"}, [2]string{"*.env.*", "ask"}),
		"edit":     tool(c, "edit"),
		"bash":     mapRules([2]string{"*", tool(c, "bash")}, [2]string{"git status*", "allow"}, [2]string{"git diff*", "allow"}, [2]string{"git log*", "allow"}, [2]string{"git fetch*", gitPermission(c, "fetch")}, [2]string{"git pull*", gitPermission(c, "pull")}, [2]string{"git commit*", gitPermission(c, "commit")}, [2]string{"git merge*", gitPermission(c, "merge")}, [2]string{"git push*", gitPermission(c, "push")}, [2]string{"git push --force*", gitPermission(c, "force_push")}, [2]string{"git push -f *", gitPermission(c, "force_push")}, [2]string{"git reset --hard*", gitPermission(c, "destructive")}, [2]string{"git clean -f*", gitPermission(c, "destructive")}, [2]string{"sudo *", "deny"}, [2]string{"su *", "deny"}, [2]string{"pkexec *", "deny"}, [2]string{"flashrom *", "deny"}, [2]string{"dfu-util *", "deny"}, [2]string{"openocd *", "deny"}, [2]string{"uhd_image_loader *", "deny"}),
		"webfetch": netPermission(c), "websearch": netPermission(c),
		"external_directory": externalPaths(c),
		"task":               "deny",
	}
	if name == "orchestrator" {
		taskRules := [][2]string{{"*", "deny"}}
		for _, a := range c.Agents {
			if a != "orchestrator" {
				taskRules = append(taskRules, [2]string{a, "allow"})
			}
		}
		p["task"] = orderedPermission{Rules: taskRules}
		p["edit"] = mapRules([2]string{"*", "deny"}, [2]string{".local-work/**", "allow"}, [2]string{".agents-opencode/logs/**", "allow"})
		// orchestrator cannot direct-write source files; specialist handoff required.
	}
	if readOnlyRole(name) {
		p["edit"] = "deny"
		p["bash"] = "deny"
	}
	if name == "code-reviewer" || name == "image-analyst" {
		p["bash"] = "deny"
	}
	if ov := c.Policy.AgentOverrides[name]; len(ov) > 0 {
		for k, v := range ov {
			if k == "task" {
				continue
			}
			if readOnlyRole(name) && (k == "bash" || k == "edit") && v != "deny" {
				continue
			}
			p[k] = v
		}
	}
	cfg := map[string]any{"model": c.Models[name], "mode": "subagent", "permission": p}
	if name == "orchestrator" {
		cfg["mode"] = "primary"
	}
	return cfg
}
func netPermission(c Config) string {
	if c.Policy.Network.Internet == "deny" {
		return "deny"
	}
	if c.Policy.Network.Internet == "allow" {
		return "allow"
	}
	return "ask"
}
func externalPaths(c Config) any {
	rules := [][2]string{{"*", tool(c, "external_directory")}}
	for _, v := range c.Policy.Paths {
		rules = append(rules, [2]string{v.Path, v.Read})
	}
	return orderedPermission{Rules: rules}
}
func contains(items []string, item string) bool {
	for _, s := range items {
		if s == item {
			return true
		}
	}
	return false
}
func configSnapshot(c Config) ([]byte, error) { return pretty(c) }
func roleSource(root, name string) ([]byte, error) {
	b, err := assets.Templates.ReadFile("agents/" + name + ".md")
	if err == nil {
		return b, nil
	}
	if !roleName.MatchString(name) {
		return nil, fmt.Errorf("invalid custom role %s", name)
	}
	b, err = os.ReadFile(filepath.Join(root, ".agents-opencode", "custom", name+".md"))
	if err != nil {
		return nil, fmt.Errorf("role %s missing from embedded catalog and custom/: %w", name, err)
	}
	return b, nil
}
func agentProfile(root, name string) ([]byte, error) {
	b, err := roleSource(root, name)
	if err != nil {
		return nil, err
	}
	content := string(b)
	if strings.HasPrefix(content, "---\n") {
		if idx := strings.Index(content[4:], "\n---"); idx >= 0 {
			content = strings.TrimSpace(content[4+idx+4:])
		}
	}
	// The definitive model, mode, and permissions live in opencode.json.
	desc := strings.ReplaceAll(name, "-", " ")
	return []byte(fmt.Sprintf("---\ndescription: \"%s specialist for the project team\"\nmode: %s\n---\n\n%s\n", desc, func() string {
		if name == "orchestrator" {
			return "primary"
		}
		return "subagent"
	}(), content)), nil
}
func registry(c Config) []byte {
	var b strings.Builder
	b.WriteString("# Installed agent team\n\nGenerated by agents-opencode. This is configuration intent, not runtime health confirmation.\n\n| Agent | Assigned model | Role |\n|---|---|---|\n")
	for _, a := range c.Agents {
		role := "Specialist"
		if a == "orchestrator" {
			role = "Primary / coordinator"
		}
		fmt.Fprintf(&b, "| `%s` | `%s` | %s |\n", a, strings.ReplaceAll(c.Models[a], "|", "\\|"), role)
	}
	b.WriteString("\nThe orchestrator must validate callable agents against OpenCode before delegation. Agent invocation and independent test evidence belong in `.local-work/ACTIVE.md`.\n")
	return []byte(b.String())
}
func agentsInstructions(c Config, original string) []byte {
	managed := begin + "\n# Agent team (managed)\n\nRead `PROJECT_BRIEF.md`, `.agents-opencode/TEAM_REGISTRY.md`, `.opencode/team/TEAM_RULES.md`, and `.opencode/team/WORKFLOW.md` before project coordination. Follow `AGENT_ACCESS_POLICY.json` within its documented enforcement limits.\n\nOnly selected agents are authorized for delegation. Track work, acceptance criteria, verification evidence, blocked items and next action in `.local-work/ACTIVE.md`. Do not pretend background work continues after the session ends.\n" + end
	if s := strings.Index(original, begin); s >= 0 {
		if e := strings.Index(original[s:], end); e >= 0 {
			return []byte(original[:s] + managed + original[s+e+len(end):])
		}
	}
	return []byte(strings.TrimRight(original, "\n") + "\n\n" + managed + "\n")
}
func Generate(root string, c Config) (map[string][]byte, error) {
	if err := c.Validate(); err != nil {
		return nil, err
	}
	result := map[string][]byte{}
	data, err := configSnapshot(c)
	if err != nil {
		return nil, err
	}
	result[configFile] = data
	op, err := opencodeConfig(root, c)
	if err != nil {
		return nil, err
	}
	result["opencode.json"] = op
	if prior, err := Load(root); err == nil {
		for _, oldRole := range prior.Agents {
			if !contains(c.Agents, oldRole) {
				result[".opencode/agents/"+oldRole+".md"] = nil // confirmed uninstall
			}
		}
	}
	for _, a := range c.Agents {
		b, err := agentProfile(root, a)
		if err != nil {
			return nil, err
		}
		result[".opencode/agents/"+a+".md"] = b
	}
	for _, name := range []string{"TEAM_RULES.md", "WORKFLOW.md", "HANDOFF_TEMPLATE.md", "ACCESS_RULES.md"} {
		b, err := assets.Templates.ReadFile("team/" + name)
		if err == nil {
			result[".opencode/team/"+name] = b
		}
	}
	result[".agents-opencode/TEAM_REGISTRY.md"] = registry(c)
	p, _ := pretty(c.Policy)
	result["AGENT_ACCESS_POLICY.json"] = p
	original, _ := os.ReadFile(filepath.Join(root, "AGENTS.md"))
	result["AGENTS.md"] = agentsInstructions(c, string(original))
	if _, err := os.Stat(filepath.Join(root, "PROJECT_BRIEF.md")); errors.Is(err, os.ErrNotExist) {
		result["PROJECT_BRIEF.md"] = []byte("# Project brief\n\nDescribe what you want to build, constraints, expected features, and acceptance criteria. The orchestrator reads this; the manager never analyzes it.\n")
	}
	return result, nil
}
func CheckManagedPaths(root string, files map[string][]byte) error {
	for rel := range files {
		clean := filepath.Clean(filepath.FromSlash(rel))
		if filepath.IsAbs(clean) || clean == ".." || strings.HasPrefix(clean, ".."+string(filepath.Separator)) {
			return fmt.Errorf("unsafe path %s", rel)
		}
		path := root
		for _, segment := range strings.Split(clean, string(filepath.Separator)) {
			path = filepath.Join(path, segment)
			fi, err := os.Lstat(path)
			if err == nil && fi.Mode()&os.ModeSymlink != 0 {
				return fmt.Errorf("refusing symlink in managed path %s", path)
			}
			if err != nil && !errors.Is(err, os.ErrNotExist) {
				return err
			}
		}
	}
	return nil
}
func Apply(root string, c Config, dry bool) ([]string, string, error) {
	files, err := Generate(root, c)
	if err != nil {
		return nil, "", err
	}
	if err = CheckManagedPaths(root, files); err != nil {
		return nil, "", err
	}
	changes := []string{}
	for rel, data := range files {
		old, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(rel)))
		if (errors.Is(err, os.ErrNotExist) && data != nil) || (err == nil && (data == nil || hash(old) != hash(data))) {
			changes = append(changes, rel)
		} else if err != nil {
			return nil, "", err
		}
	}
	sort.Strings(changes)
	if dry || len(changes) == 0 {
		return changes, "", nil
	}
	dir, err := backup(root, changes)
	if err != nil {
		return nil, "", err
	}
	for _, rel := range changes {
		if files[rel] == nil {
			err = os.Remove(filepath.Join(root, filepath.FromSlash(rel)))
		} else {
			err = writeAtomic(filepath.Join(root, filepath.FromSlash(rel)), files[rel])
		}
		if err != nil {
			return changes, dir, fmt.Errorf("write %s failed: %w; backups at %s", rel, err, dir)
		}
	}
	return changes, dir, nil
}
