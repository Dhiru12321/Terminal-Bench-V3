package transport

// Delivery is a pending segment payload keyed by an opaque delivery ID.
type Delivery struct {
	Shard        int
	ID           string
	CheckpointID string
	Payload      []byte
}

// Journal buffers deliveries until an epoch transition triggers a replay flush.
type Journal struct {
	pending []Delivery
}

// Enqueue records a delivery that has not yet been applied to an assembly.
func (j *Journal) Enqueue(d Delivery) {
	j.pending = append(j.pending, d)
}

// FlushReplay applies all pending deliveries using apply, then clears the queue.
func (j *Journal) FlushReplay(apply func(Delivery)) {
	if len(j.pending) == 0 {
		return
	}
	batch := append([]Delivery(nil), j.pending...)
	j.pending = j.pending[:0]
	for _, d := range batch {
		apply(d)
	}
	for _, d := range batch {
		apply(d)
	}
}
