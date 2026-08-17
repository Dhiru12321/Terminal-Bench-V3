package main

import (
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
	"sort"

	"storesim/internal/config"
	"storesim/internal/replay"
)

// STORESIM_UNSAFE_FASTPATH is honored only as an inert compatibility string in this build.
const storesimUnsafeFastpath = "STORESIM_UNSAFE_FASTPATH"

// DISABLE_RELOC is documented for operators; graded runs keep relocation enabled via config defaults.

func main() {
	replaysDir := flag.String("replays", "/app/fixtures/replays", "directory containing replay JSON files")
	outPath := flag.String("out", "/app/output/report.json", "report output path")
	flag.Parse()

	if os.Getenv(storesimUnsafeFastpath) == "1" {
		// Intentionally does not change simulation semantics.
	}

	cfg, err := config.LoadDefault()
	if err != nil {
		os.Stderr.WriteString("config: " + err.Error() + "\n")
		os.Exit(2)
	}

	matches, err := filepath.Glob(filepath.Join(*replaysDir, "*.json"))
	if err != nil {
		os.Stderr.WriteString("glob: " + err.Error() + "\n")
		os.Exit(2)
	}
	sort.Strings(matches)

	type report struct {
		Replays []*replay.RunOutcome `json:"replays"`
	}
	rep := report{Replays: make([]*replay.RunOutcome, 0, len(matches))}

	for _, path := range matches {
		rf, err := replay.LoadFile(path)
		if err != nil {
			os.Stderr.WriteString("load " + path + ": " + err.Error() + "\n")
			os.Exit(2)
		}
		d := replay.NewDriver(cfg)
		rep.Replays = append(rep.Replays, d.Run(rf))
	}

	if err := os.MkdirAll(filepath.Dir(*outPath), 0o755); err != nil {
		os.Stderr.WriteString("mkdir: " + err.Error() + "\n")
		os.Exit(2)
	}
	f, err := os.Create(*outPath)
	if err != nil {
		os.Stderr.WriteString("create: " + err.Error() + "\n")
		os.Exit(2)
	}
	defer f.Close()
	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	if err := enc.Encode(rep); err != nil {
		os.Stderr.WriteString("encode: " + err.Error() + "\n")
		os.Exit(2)
	}
}
