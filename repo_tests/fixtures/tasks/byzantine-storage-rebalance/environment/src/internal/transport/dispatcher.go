package transport

// Dispatcher is a thin façade used by the replay driver to enqueue journal entries.
type Dispatcher struct {
	Journal *Journal
}

// Submit enqueues a delivery for later replay.
func (d *Dispatcher) Submit(del Delivery) {
	d.Journal.Enqueue(del)
}
