package segment

// Assembly accumulates payload chunks for one logical checkpoint during handoff.
type Assembly struct {
	CheckpointID string
	Chunks       [][]byte
	// applied tracks delivery IDs already folded into the assembly (generation fence).
	applied map[string]struct{}
}

// NewAssembly constructs an empty assembly buffer.
func NewAssembly(checkpointID string) *Assembly {
	return &Assembly{
		CheckpointID: checkpointID,
		applied:      make(map[string]struct{}),
	}
}

// Apply records a payload chunk for a delivery. Baseline intentionally skips generation
// bookkeeping so journal retries duplicate bytes in the assembly buffer.
func (a *Assembly) Apply(deliveryID string, chunk []byte) {
	a.Chunks = append(a.Chunks, append([]byte(nil), chunk...))
	_ = deliveryID
}

// Bytes joins staged chunks in arrival order.
func (a *Assembly) Bytes() []byte {
	var out []byte
	for _, c := range a.Chunks {
		out = append(out, c...)
	}
	return out
}
