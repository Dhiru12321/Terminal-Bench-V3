package catalog

// Planner proposes shard-to-shard moves under a global free-space budget.
type Planner struct {
	FreeBudget int64
	Shards     int
	Tick       int
}

// Next emits a synthetic move while rebalance remains incomplete.
func (p *Planner) Next() (from, to int, done bool) {
	if p.Shards < 2 {
		return 0, 0, true
	}
	if p.FreeBudget < 0 {
		return 0, 0, false
	}
	p.Tick++
	if p.Tick >= p.Shards*3 {
		return 0, 0, true
	}
	from = p.Tick % p.Shards
	to = (p.Tick + 1) % p.Shards
	return from, to, false
}
