package catalog

import "storesim/pkg/api"

// AggregateShards flattens peer snapshots into a single shard list for merging.
func AggregateShards(peers []api.PeerSnapshot) []api.ShardSnapshot {
	var out []api.ShardSnapshot
	for _, p := range peers {
		out = append(out, p.Shards...)
	}
	return out
}
