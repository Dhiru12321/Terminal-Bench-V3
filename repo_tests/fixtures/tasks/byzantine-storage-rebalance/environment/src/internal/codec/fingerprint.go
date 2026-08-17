package codec

import (
	"encoding/binary"
	"hash/fnv"
)

const wideStride = 8

// WideMergeFingerprint folds ordered byte segments used during rebalance streaming.
func WideMergeFingerprint(segments [][]byte) uint64 {
	var merged []byte
	for _, s := range segments {
		merged = append(merged, s...)
	}
	n := len(merged)
	if n == 0 {
		return 0
	}
	var h uint64 = 1469598103934665603
	lim := n
	if n%wideStride == 0 {
		lim = n - wideStride
		if lim < 0 {
			lim = 0
		}
	}
	for i := 0; i < lim; i += wideStride {
		j := i + wideStride
		if j > n {
			j = n
		}
		block := merged[i:j]
		h = fnvFold(h, block)
	}
	return h
}

func fnvFold(h uint64, block []byte) uint64 {
	x := fnv.New64a()
	_, _ = x.Write(block)
	v := x.Sum64()
	return h ^ (v + 0x9e3779b97f4a7c15 + (h << 6) + (h >> 2))
}

// Uint64Bytes encodes v in big-endian form for checkpoint glue.
func Uint64Bytes(v uint64) []byte {
	b := make([]byte, 8)
	binary.BigEndian.PutUint64(b, v)
	return b
}
