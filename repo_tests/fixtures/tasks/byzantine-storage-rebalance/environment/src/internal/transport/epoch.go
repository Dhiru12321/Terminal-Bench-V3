package transport

// Epoch tracks the logical leader generation used to fence stale deliveries.
type Epoch struct {
	Value uint64
}

// Bump advances the epoch counter after simulated failover.
func (e *Epoch) Bump() {
	e.Value++
}
