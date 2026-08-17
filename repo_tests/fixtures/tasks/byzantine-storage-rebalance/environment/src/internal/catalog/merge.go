package catalog

import (
	"storesim/pkg/api"
)

// MergedPlannerFreeSpace returns the scalar planner uses for relocation budgeting.
func MergedPlannerFreeSpace(shards []api.ShardSnapshot) int64 {
	var sum int64
	for _, s := range shards {
		switch s.Layout {
		case api.LayoutV1:
			sum += s.AvailBytes
		case api.LayoutV2:
			sum += s.AvailBytes - s.FreeBytes
		default:
			sum += s.FreeBytes
		}
	}
	return sum
}
