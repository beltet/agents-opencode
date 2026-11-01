package manager

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/beltet/agents-opencode/assets"
)

const Version = "3.0.0-beta.1"
const configFile = ".agents-opencode/config.json"

var roleName = regexp.MustCompile(`^[a-z][a-z0-9-]{1,63}$`)
var tri = map[string]bool{"allow": true, "ask": true, "deny": true}

// Policy is user intent; not a host firewall or sandbox.
type Policy struct {
	Tools          map[string]string            `json:"tools"`
	Git            map[string]string            `json:"git"`
	Network        NetworkRules                 `json:"network"`
	Paths          []PathRule                   `json:"paths,omitempty"`
	Devices        []DeviceRule                 `json:"devices,omitempty"`
	AgentOverrides map[string]map[string]string `json:"agent_overrides,omitempty"`
	Unattended     bool                         `json:"unattended"`
}
type NetworkRules struct {
	Internet string   `json:"internet"`
	Allow    []string `json:"allow,omitempty"`
	Deny     []string `json:"deny,omitempty"`
}
type PathRule struct {
	Path  string `json:"path"`
	Read  string `json:"read"`
	Write string `json:"write"`
	Kind  string `json:"kind,omitempty"`
}
type DeviceRule struct {
	Identifier string `json:"identifier"`
	Access     string `json:"access"`
	Flash      string `json:"flash"`
}
type GitSettings struct {
	Mode        string `json:"mode"`
	Remote      string `json:"remote,omitempty"`
	URL         string `json:"url,omitempty"`
	SSHHost     string `json:"ssh_host,omitempty"`
	SSHPort     int    `json:"ssh_port,omitempty"`
	SSHUser     string `json:"ssh_user,omitempty"`
	SSHIdentity string `json:"ssh_identity,omitempty"`
	AuthorName  string `json:"author_name,omitempty"`
	AuthorEmail string `json:"author_email,omitempty"`
	Branch      string `json:"branch,omitempty"`
}
type Config struct {
	Version int               `json:"version"`
	Agents  []string          `json:"agents"`
	Models  map[string]string `json:"models"`
	Policy  Policy            `json:"policy"`
	Git     GitSettings       `json:"git"`
}

func Default() Config {
	return Config{Version: 3, Agents: []string{}, Models: map[string]string{}, Policy: Policy{
		Tools:   map[string]string{"read": "allow", "edit": "allow", "bash": "ask", "webfetch": "ask", "websearch": "ask", "external_directory": "deny"},
		Git:     map[string]string{"fetch": "ask", "pull": "ask", "commit": "ask", "push": "deny", "merge": "ask", "force_push": "deny", "destructive": "deny"},
		Network: NetworkRules{Internet: "ask"}, AgentOverrides: map[string]map[string]string{},
	}, Git: GitSettings{Mode: "local", Remote: "origin", SSHPort: 22, Branch: "main"}}
}
func rootPath(root string) (string, error) {
	abs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	fi, err := os.Stat(abs)
	if err != nil {
		return "", err
	}
	if !fi.IsDir() {
		return "", fmt.Errorf("not a directory: %s", abs)
	}
	return abs, nil
}
func ConfigPath(root string) string { return filepath.Join(root, filepath.FromSlash(configFile)) }
func Load(root string) (Config, error) {
	data, err := os.ReadFile(ConfigPath(root))
	if err != nil {
		return Config{}, err
	}
	var c Config
	if err = json.Unmarshal(data, &c); err != nil {
		return c, err
	}
	return c, c.Validate()
}
func (c Config) Validate() error {
	if c.Version != 3 {
		return fmt.Errorf("unsupported manager format %d (expected 3); use migrate or backup first", c.Version)
	}
	if len(c.Agents) == 0 {
		return errors.New("select at least one agent")
	}
	seen := map[string]bool{}
	for _, name := range c.Agents {
		if !roleName.MatchString(name) {
			return fmt.Errorf("invalid agent name %q", name)
		}
		if seen[name] {
			return fmt.Errorf("duplicate agent %s", name)
		}
		seen[name] = true
		if strings.TrimSpace(c.Models[name]) == "" {
			return fmt.Errorf("no model selected for %s", name)
		}
	}
	for _, v := range c.Policy.Tools {
		if !tri[v] {
			return fmt.Errorf("invalid tool permission %q", v)
		}
	}
	for _, v := range c.Policy.Git {
		if !tri[v] {
			return fmt.Errorf("invalid git permission %q", v)
		}
	}
	if !tri[c.Policy.Network.Internet] {
		return fmt.Errorf("invalid internet permission %q", c.Policy.Network.Internet)
	}
	for _, p := range c.Policy.Paths {
		if p.Path == "" || !tri[p.Read] || !tri[p.Write] {
			return fmt.Errorf("invalid path rule %+v", p)
		}
	}
	for _, d := range c.Policy.Devices {
		if d.Identifier == "" || !tri[d.Access] || !tri[d.Flash] {
			return fmt.Errorf("invalid device rule %+v", d)
		}
	}
	for role, p := range c.Policy.AgentOverrides {
		if !seen[role] {
			return fmt.Errorf("unknown agent override: %s", role)
		}
		for _, val := range p {
			if !tri[val] {
				return fmt.Errorf("invalid agent override: %s", val)
			}
		}
	}
	if c.Git.SSHPort < 0 || c.Git.SSHPort > 65535 {
		return errors.New("SSH port must be 1..65535 or unspecified")
	}
	if c.Git.Mode != "local" && c.Git.Mode != "existing" && c.Git.Mode != "remote" {
		return fmt.Errorf("invalid Git mode %s", c.Git.Mode)
	}
	if c.Git.Mode == "remote" && (c.Git.URL == "" || strings.ContainsAny(c.Git.URL, "\n\r")) {
		return errors.New("remote mode requires a valid nonempty URL")
	}
	return nil
}
func Catalog() ([]string, error) {
	names, err := assets.Templates.ReadDir("agents")
	if err != nil {
		return nil, err
	}
	result := []string{}
	for _, n := range names {
		if !n.IsDir() && strings.HasSuffix(n.Name(), ".md") {
			result = append(result, strings.TrimSuffix(n.Name(), ".md"))
		}
	}
	sort.Strings(result)
	return result, nil
}
func AvailableRole(name string) bool {
	if !roleName.MatchString(name) {
		return false
	}
	_, err := assets.Templates.ReadFile("agents/" + name + ".md")
	return err == nil
}
func hash(data []byte) string { h := sha256.Sum256(data); return hex.EncodeToString(h[:]) }
func pretty(value any) ([]byte, error) {
	data, err := json.MarshalIndent(value, "", "  ")
	return append(data, '\n'), err
}
func backup(root string, paths []string) (string, error) {
	stamp := time.Now().UTC().Format("20060102T150405.000000000Z")
	target := filepath.Join(root, ".agents-opencode", "backups", stamp)
	seen := map[string]bool{}
	count := 0
	for _, rel := range paths {
		if seen[rel] {
			continue
		}
		seen[rel] = true
		src := filepath.Join(root, filepath.FromSlash(rel))
		b, err := os.ReadFile(src)
		if errors.Is(err, os.ErrNotExist) {
			continue
		}
		if err != nil {
			return "", err
		}
		dst := filepath.Join(target, filepath.FromSlash(rel))
		if err = os.MkdirAll(filepath.Dir(dst), 0700); err != nil {
			return "", err
		}
		if err = os.WriteFile(dst, b, 0600); err != nil {
			return "", err
		}
		count++
	}
	if count == 0 {
		return "", nil
	}
	return target, nil
}
func writeAtomic(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	t, err := os.CreateTemp(filepath.Dir(path), ".agents-opencode-*")
	if err != nil {
		return err
	}
	defer os.Remove(t.Name())
	if _, err = t.Write(data); err != nil {
		t.Close()
		return err
	}
	if err = t.Chmod(0644); err != nil {
		t.Close()
		return err
	}
	if err = t.Sync(); err != nil {
		t.Close()
		return err
	}
	if err = t.Close(); err != nil {
		return err
	}
	if err = os.Rename(t.Name(), path); err != nil {
		return err
	}
	return nil
}
func writeConfig(root string, c Config) error {
	b, err := pretty(c)
	if err != nil {
		return err
	}
	return writeAtomic(ConfigPath(root), b)
}
