package replay

import (
	"encoding/json"
	"os"

	"storesim/pkg/api"
)

// LoadFile reads a replay JSON bundle from disk.
func LoadFile(path string) (*api.ReplayFile, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var rf api.ReplayFile
	if err := json.Unmarshal(raw, &rf); err != nil {
		return nil, err
	}
	return &rf, nil
}
