package codec

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"math"
)

// CanonicalTensorBytes lays out float64 values row-major as big-endian IEEE754.
func CanonicalTensorBytes(rows, cols int, values []float64) ([]byte, error) {
	want := rows * cols
	if len(values) != want {
		return nil, fmt.Errorf("tensor values: want %d got %d", want, len(values))
	}
	out := make([]byte, 8*want)
	for i, v := range values {
		binary.BigEndian.PutUint64(out[i*8:], math.Float64bits(v))
	}
	return out, nil
}

// BindWideFingerprint appends a big-endian fingerprint tag after canonical tensor bytes.
func BindWideFingerprint(tensor []byte, wideFP uint64) []byte {
	tag := make([]byte, 8)
	binary.BigEndian.PutUint64(tag, wideFP)
	out := make([]byte, 0, len(tensor)+8)
	out = append(out, tensor...)
	out = append(out, tag...)
	return out
}

// HexSHA256 returns lowercase hex of SHA-256 over b.
func HexSHA256(b []byte) string {
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}
