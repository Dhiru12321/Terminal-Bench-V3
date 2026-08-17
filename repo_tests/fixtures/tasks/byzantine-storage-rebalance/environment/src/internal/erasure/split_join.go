package erasure

// SplitFixed chunks buf into segments of width bytes (last segment zero-padded).
func SplitFixed(buf []byte, width int) [][]byte {
	if width <= 0 {
		return nil
	}
	var out [][]byte
	for i := 0; i < len(buf); i += width {
		end := i + width
		if end > len(buf) {
			end = len(buf)
		}
		seg := make([]byte, width)
		copy(seg, buf[i:end])
		out = append(out, seg)
	}
	if len(buf) == 0 {
		return [][]byte{make([]byte, width)}
	}
	return out
}

// Join concatenates segment payloads trimming trailing padding zeros for fingerprint source.
func Join(segments [][]byte) []byte {
	var out []byte
	for _, s := range segments {
		out = append(out, s...)
	}
	return out
}
