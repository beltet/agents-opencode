package manager

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func testConfig() Config {
	c := Default()
	c.Agents = []string{"orchestrator", "software-engineer", "verification-engineer", "code-reviewer"}
	for _, a := range c.Agents {
		c.Models[a] = "example/manual-model"
	}
	return c
}
func TestCatalog23(t *testing.T) {
	roles, err := Catalog()
	if err != nil {
		t.Fatal(err)
	}
	if len(roles) != 23 {
		t.Fatalf("want 23, got %d", len(roles))
	}
	for _, n := range []string{"orchestrator", "software-engineer", "code-reviewer", "verification-engineer", "image-analyst"} {
		if !contains(roles, n) {
			t.Fatalf("missing %s", n)
		}
	}
}
func TestConfigRequiresManualModels(t *testing.T) {
	c := Default()
	if c.Validate() == nil {
		t.Fatal("missing models accepted")
	}
	c = testConfig()
	if err := c.Validate(); err != nil {
		t.Fatal(err)
	}
	c.Policy.Network.Internet = "yes"
	if c.Validate() == nil {
		t.Fatal("bad permission accepted")
	}
}
func TestInstallPreservesUnmanaged(t *testing.T) {
	root := t.TempDir()
	c := testConfig()
	original := []byte(`{"theme":"custom","agent":{"my-role":{"model":"local/custom"}},"permission":{"webfetch":"deny"}}`)
	if err := os.WriteFile(filepath.Join(root, "opencode.json"), original, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "AGENTS.md"), []byte("# user rules\n"), 0600); err != nil {
		t.Fatal(err)
	}
	changed, _, err := Apply(root, c, false)
	if err != nil {
		t.Fatal(err)
	}
	if len(changed) < 5 {
		t.Fatalf("unexpectedly few output files: %d", len(changed))
	}
	b, err := os.ReadFile(filepath.Join(root, "opencode.json"))
	if err != nil {
		t.Fatal(err)
	}
	var obj map[string]any
	if err = json.Unmarshal(b, &obj); err != nil {
		t.Fatal(err)
	}
	if obj["theme"] != "custom" {
		t.Fatal("theme overwritten")
	}
	if obj["permission"] == nil {
		t.Fatal("unmanaged permission removed")
	}
	ag := obj["agent"].(map[string]any)
	if ag["my-role"] == nil {
		t.Fatal("custom agent removed")
	}
	orc := ag["orchestrator"].(map[string]any)
	perms := orc["permission"].(map[string]any)
	if perms["task"] == nil {
		t.Fatal("orchestrator task rules not generated")
	}
	if perms["edit"].(map[string]any)["*"] != "deny" {
		t.Fatal("orchestrator can edit source")
	}
	if ag["code-reviewer"].(map[string]any)["permission"].(map[string]any)["bash"] != "deny" {
		t.Fatal("read-only reviewer can shell")
	}
	a, _ := os.ReadFile(filepath.Join(root, "AGENTS.md"))
	if !strings.Contains(string(a), "# user rules") || !strings.Contains(string(a), begin) {
		t.Fatal("user AGENTS.md lost")
	}
	// Determinism / idempotence
	again, _, err := Apply(root, c, true)
	if err != nil {
		t.Fatal(err)
	}
	if len(again) > 0 {
		t.Fatalf("not idempotent: %v", again)
	}
}
func TestBackupsOnUpdate(t *testing.T) {
	root := t.TempDir()
	c := testConfig()
	if _, _, err := Apply(root, c, false); err != nil {
		t.Fatal(err)
	}
	c.Models["software-engineer"] = "another/manual"
	changes, d, err := Apply(root, c, false)
	if err != nil {
		t.Fatal(err)
	}
	if d == "" || len(changes) == 0 {
		t.Fatalf("no backup: %s", d)
	}
	b, err := os.ReadFile(filepath.Join(d, "opencode.json"))
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Contains(b, []byte("another/manual")) {
		t.Fatal("backup reflects new, not old value")
	}
}
func TestSymlinkDenied(t *testing.T) {
	root := t.TempDir()
	other := t.TempDir()
	if err := os.Symlink(other, filepath.Join(root, ".opencode")); err != nil {
		t.Skip(err)
	}
	_, _, err := Apply(root, testConfig(), true)
	if err == nil {
		t.Fatal("symlink attack allowed")
	}
}
func TestRejectBadExistingJSON(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "opencode.json"), []byte(`{"agent": { /* comment */ }}`), 0600); err != nil {
		t.Fatal(err)
	}
	_, _, err := Apply(root, testConfig(), true)
	if err == nil {
		t.Fatal("invalid existing config overwritten")
	}
}
func TestSecurityAdvisoryAndTaskRules(t *testing.T) {
	root := t.TempDir()
	c := testConfig()
	c.Policy.Network.Deny = []string{"evil.example"}
	c.Policy.Devices = []DeviceRule{{Identifier: "1d50:6089", Access: "ask", Flash: "deny"}}
	if _, _, err := Apply(root, c, false); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(filepath.Join(root, "AGENT_ACCESS_POLICY.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(b, []byte("evil.example")) {
		t.Fatal("network intent not retained")
	}
	var obj map[string]any
	b, err = os.ReadFile(filepath.Join(root, "opencode.json"))
	if err != nil {
		t.Fatal(err)
	}
	if err = json.Unmarshal(b, &obj); err != nil {
		t.Fatal(err)
	}
	agents := obj["agent"].(map[string]any)
	task := agents["orchestrator"].(map[string]any)["permission"].(map[string]any)["task"].(map[string]any)
	if task["software-engineer"] != "allow" || task["orchestrator"] != nil {
		t.Fatalf("wrong task permissions %+v", task)
	}
	for _, a := range c.Agents {
		if a == "orchestrator" {
			continue
		}
		perm := agents[a].(map[string]any)["permission"].(map[string]any)
		if perm["task"] != "deny" {
			t.Fatalf("%s can recursively delegate", a)
		}
	}
}
func TestCLIManualWizard(t *testing.T) {
	root := t.TempDir()
	input := "3,11,17,23\nn\nexample/manual\n\n\n\n\nn\nn\ny\nmy example project\n" // defaults: four roles, bulk model, permissions no, git no, confirm yes, summary
	var output bytes.Buffer
	if err := Launch([]string{"install", "--project=" + root}, strings.NewReader(input), &output); err != nil {
		t.Fatal(err)
	}
	c, err := Load(root)
	if err != nil {
		t.Fatalf("wizard: %v; output:\n%s", err, output.String())
	}
	for _, a := range c.Agents {
		if c.Models[a] != "example/manual" {
			t.Fatalf("missing bulk model for %s", a)
		}
	}
	brief, err := os.ReadFile(filepath.Join(root, "PROJECT_BRIEF.md"))
	if err != nil || !bytes.Contains(brief, []byte("my example project")) {
		t.Fatalf("project brief not saved: %q / %v", brief, err)
	}
}
func TestRestorePathIsolation(t *testing.T) {
	root := t.TempDir()
	u := NewUI(strings.NewReader("y\n"), &bytes.Buffer{}, "en")
	if err := restoreCommand(u, root, "/tmp/not-a-backup"); err == nil {
		t.Fatal("untrusted restore location allowed")
	}
}
func TestGitModeRequiresURL(t *testing.T) {
	c := testConfig()
	c.Git.Mode = "remote"
	if c.Validate() == nil {
		t.Fatal("missing remote URL allowed")
	}
}

func TestDisableAgentRemovesOnlyManaged(t *testing.T) {
	root := t.TempDir()
	c := testConfig()
	if _, _, err := Apply(root, c, false); err != nil {
		t.Fatal(err)
	}
	// This unrelated agent must remain untouched.
	objpath := filepath.Join(root, "opencode.json")
	b, _ := os.ReadFile(objpath)
	var obj map[string]any
	_ = json.Unmarshal(b, &obj)
	obj["agent"].(map[string]any)["unmanaged"] = map[string]any{"model": "custom/keep"}
	b, _ = json.Marshal(obj)
	_ = os.WriteFile(objpath, b, 0600)
	c.Agents = []string{"orchestrator", "software-engineer"}
	changes, _, err := Apply(root, c, true)
	if err != nil {
		t.Fatal(err)
	}
	if !contains(changes, ".opencode/agents/verification-engineer.md") {
		t.Fatalf("missing removal in preview: %v", changes)
	}
	if _, _, err = Apply(root, c, false); err != nil {
		t.Fatal(err)
	}
	if _, err = os.Stat(filepath.Join(root, ".opencode/agents/verification-engineer.md")); !os.IsNotExist(err) {
		t.Fatal("deselected profile still installed")
	}
	b, _ = os.ReadFile(objpath)
	_ = json.Unmarshal(b, &obj)
	ag := obj["agent"].(map[string]any)
	if ag["verification-engineer"] != nil || ag["unmanaged"] == nil {
		t.Fatal("wrong agent deletion")
	}
}
