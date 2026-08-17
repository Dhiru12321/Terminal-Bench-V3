package api

// CatalogLayout marks which snapshot wire format a peer last published.
type CatalogLayout int

const (
	LayoutV1 CatalogLayout = 1
	LayoutV2 CatalogLayout = 2
)

// ShardSnapshot is a single shard's accounting fields under one layout version.
type ShardSnapshot struct {
	ShardID int           `json:"shard_id"`
	Layout  CatalogLayout `json:"layout"`
	// V1 names the field "avail" on the wire; V2 uses "free" for the same semantic.
	AvailBytes int64 `json:"avail_bytes"`
	FreeBytes  int64 `json:"free_bytes"`
}

// PeerSnapshot aggregates shard rows for planner input.
type PeerSnapshot struct {
	PeerID string          `json:"peer_id"`
	Shards []ShardSnapshot `json:"shards"`
}

// ReplayEvent is one step in a bundled JSON trace.
type ReplayEvent struct {
	Type string `json:"type"`

	Epoch int `json:"epoch,omitempty"`

	Shard int    `json:"shard,omitempty"`
	ID    string `json:"id,omitempty"`

	PayloadHex string `json:"payload_hex,omitempty"`

	CheckpointID string `json:"checkpoint_id,omitempty"`
	Rows         int    `json:"rows,omitempty"`
	Cols         int    `json:"cols,omitempty"`
	Values       []float64 `json:"values,omitempty"`

	SegmentsHex []string `json:"segments_hex,omitempty"`

	Peers []PeerSnapshot `json:"peers,omitempty"`

	MaxTicks int `json:"max_ticks,omitempty"`
}

// ReplayFile is the on-disk JSON contract for fixtures.
type ReplayFile struct {
	Name        string           `json:"name"`
	Checkpoints []CheckpointSpec `json:"checkpoints"`
	Events      []ReplayEvent    `json:"events"`
}

// CheckpointSpec describes expected tensor geometry for golden hashing.
type CheckpointSpec struct {
	ID          string    `json:"id"`
	Rows        int       `json:"rows"`
	Cols        int       `json:"cols"`
	Values      []float64 `json:"values"`
	SegmentsHex []string  `json:"segments_hex,omitempty"`
}
