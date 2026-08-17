package segment

import (
	"encoding/hex"
	"fmt"

	"storesim/internal/codec"
)

// WideFingerprintFromHexSegments decodes hex payloads and folds them through the wide buffer path.
func WideFingerprintFromHexSegments(segmentsHex []string) (uint64, error) {
	var parts [][]byte
	for i, hx := range segmentsHex {
		b, err := hex.DecodeString(hx)
		if err != nil {
			return 0, fmt.Errorf("segment %d: %w", i, err)
		}
		parts = append(parts, b)
	}
	return codec.WideMergeFingerprint(parts), nil
}
