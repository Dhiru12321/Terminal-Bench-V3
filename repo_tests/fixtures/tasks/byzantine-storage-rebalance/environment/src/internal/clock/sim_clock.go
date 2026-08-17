package clock

// SimClock advances only when the driver asks; no wall time.
type SimClock struct {
	Ticks int64
}

func (c *SimClock) Step() {
	c.Ticks++
}

func (c *SimClock) Steps() int {
	return int(c.Ticks)
}
