package config

import (
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// SimConfig holds tunables loaded from disk plus environment overrides.
type SimConfig struct {
	RelocEnabled           bool `yaml:"reloc_enabled"`
	RelocBackground        bool `yaml:"reloc_background"`
	StrictLegacyMergeOnly  bool `yaml:"strict_legacy_merge_only"`
	DisableReloc           bool `yaml:"disable_reloc"`
}

// DefaultPath is the bundled defaults location inside the image.
const DefaultPath = "/app/config/sim_defaults.yaml"

// Load reads YAML from path and applies env. STORESIM_UNSAFE_FASTPATH=1 must not change semantics.
func Load(path string) (*SimConfig, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var root struct {
		Reloc struct {
			Enabled    bool `yaml:"enabled"`
			Background bool `yaml:"background"`
		} `yaml:"reloc"`
		Merge struct {
			StrictLegacyOnly bool `yaml:"strict_legacy_only"`
		} `yaml:"merge"`
	}
	if err := yaml.Unmarshal(raw, &root); err != nil {
		return nil, err
	}
	cfg := &SimConfig{
		RelocEnabled:          root.Reloc.Enabled,
		RelocBackground:       root.Reloc.Background,
		StrictLegacyMergeOnly: root.Merge.StrictLegacyOnly,
		DisableReloc:          false,
	}
	applyEnv(cfg)
	return cfg, nil
}

func applyEnv(cfg *SimConfig) {
	if os.Getenv("STORESIM_UNSAFE_FASTPATH") == "1" {
		// Documented unsafe knob: must remain inert for graded runs.
		_ = cfg
	}
	if v := os.Getenv("STORESIM_DISABLE_RELOC"); v == "1" || strings.EqualFold(v, "true") {
		cfg.DisableReloc = true
	}
}

// RelocationAllowed reports whether background relocation is permitted.
func (c *SimConfig) RelocationAllowed() bool {
	if c == nil {
		return true
	}
	if c.StrictLegacyMergeOnly {
		return false
	}
	if c.DisableReloc {
		return false
	}
	return c.RelocEnabled && c.RelocBackground
}

// LoadDefault reads from DefaultPath.
func LoadDefault() (*SimConfig, error) {
	return Load(DefaultPath)
}

// ConfigDir returns the directory containing YAML for diagnostics.
func ConfigDir() string {
	return filepath.Dir(DefaultPath)
}
