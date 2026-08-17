package replay

import (
	"encoding/hex"
	"fmt"
	"strings"

	"storesim/internal/catalog"
	"storesim/internal/clock"
	"storesim/internal/codec"
	"storesim/internal/config"
	"storesim/internal/segment"
	"storesim/internal/transport"
	"storesim/pkg/api"
)

// RunOutcome captures one replay execution summary.
type RunOutcome struct {
	Name            string              `json:"name"`
	FinishReason    string              `json:"finish_reason"`
	Steps           int                 `json:"steps"`
	DeliveryApplies int                 `json:"delivery_applies"`
	RelocTicks      int                 `json:"reloc_ticks"`
	Checkpoints     []CheckpointOutcome `json:"checkpoints"`
}

// CheckpointOutcome is one materialized tensor digest line.
type CheckpointOutcome struct {
	ID              string `json:"id"`
	TensorSHA256Hex string `json:"tensor_sha256_hex"`
}

// Driver executes one replay file against simulator state.
type Driver struct {
	cfg         *config.SimConfig
	clk         *clock.SimClock
	journal     *transport.Journal
	dispatcher  *transport.Dispatcher
	epoch       *transport.Epoch
	assemblies map[string]*segment.Assembly
	applies    int
	relocTicks int
	// rebPlanner carries tick state across inner rebalance_loop iterations.
	rebPlanner *catalog.Planner
	checkpoints []api.CheckpointSpec
}

// NewDriver wires subsystems for a single replay run.
func NewDriver(cfg *config.SimConfig) *Driver {
	j := &transport.Journal{}
	return &Driver{
		cfg:         cfg,
		clk:         &clock.SimClock{},
		journal:     j,
		dispatcher:  &transport.Dispatcher{Journal: j},
		epoch:       &transport.Epoch{},
		assemblies:  make(map[string]*segment.Assembly),
		checkpoints: nil,
	}
}

func (d *Driver) assemblyFor(id string) *segment.Assembly {
	if a, ok := d.assemblies[id]; ok {
		return a
	}
	a := segment.NewAssembly(id)
	d.assemblies[id] = a
	return a
}

// Run executes rf and returns an outcome; errors downgrade to a non-complete finish reason.
func (d *Driver) Run(rf *api.ReplayFile) *RunOutcome {
	d.rebPlanner = nil
	out := &RunOutcome{Name: rf.Name, FinishReason: "complete"}
	var runErr error
	for _, ev := range rf.Events {
		d.clk.Step()
		if err := d.handleEvent(ev); err != nil {
			runErr = err
			break
		}
	}
	if runErr != nil {
		if strings.Contains(runErr.Error(), "rebalance step limit") {
			out.FinishReason = "step_limit"
		} else {
			out.FinishReason = "deadlock"
		}
	}
	out.Steps = d.clk.Steps()
	out.DeliveryApplies = d.applies
	out.RelocTicks = d.relocTicks
	for _, spec := range rf.Checkpoints {
		co, err := d.digestCheckpoint(spec)
		if err != nil {
			out.FinishReason = "deadlock"
			break
		}
		out.Checkpoints = append(out.Checkpoints, co)
	}
	return out
}

func (d *Driver) handleEvent(ev api.ReplayEvent) error {
	switch ev.Type {
	case "noop":
		return nil
	case "segment_enqueue":
		payload, err := hex.DecodeString(ev.PayloadHex)
		if err != nil {
			return fmt.Errorf("segment_enqueue: %w", err)
		}
		d.dispatcher.Submit(transport.Delivery{
			Shard:        ev.Shard,
			ID:           ev.ID,
			CheckpointID: ev.CheckpointID,
			Payload:      payload,
		})
		return nil
	case "epoch_bump":
		d.epoch.Bump()
		d.journal.FlushReplay(func(del transport.Delivery) {
			d.applies++
			d.assemblyFor(del.CheckpointID).Apply(del.ID, del.Payload)
		})
		return nil
	case "rebalance_tick":
		if !d.cfg.RelocationAllowed() {
			return fmt.Errorf("rebalance requested while relocation disallowed")
		}
		d.relocTicks++
		shards := catalog.AggregateShards(ev.Peers)
		free := catalog.MergedPlannerFreeSpace(shards)
		pl := &catalog.Planner{FreeBudget: free, Shards: maxInt(2, len(shards))}
		_, _, _ = pl.Next()
		return nil
	case "rebalance_loop":
		maxTicks := ev.MaxTicks
		if maxTicks <= 0 {
			maxTicks = 256
		}
		shards := catalog.AggregateShards(ev.Peers)
		free := catalog.MergedPlannerFreeSpace(shards)
		if free < 0 {
			return fmt.Errorf("negative free budget")
		}
		if !d.cfg.RelocationAllowed() {
			return fmt.Errorf("rebalance_loop: relocation disabled")
		}
		d.rebPlanner = &catalog.Planner{FreeBudget: free, Shards: maxInt(2, len(shards))}
		for i := 0; i < maxTicks; i++ {
			d.clk.Step()
			d.relocTicks++
			_, _, done := d.rebPlanner.Next()
			if done {
				d.rebPlanner = nil
				return nil
			}
		}
		d.rebPlanner = nil
		return fmt.Errorf("rebalance step limit")
	default:
		return fmt.Errorf("unknown event type %q", ev.Type)
	}
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func (d *Driver) digestCheckpoint(spec api.CheckpointSpec) (CheckpointOutcome, error) {
	tensor, err := codec.CanonicalTensorBytes(spec.Rows, spec.Cols, spec.Values)
	if err != nil {
		return CheckpointOutcome{}, err
	}
	if len(spec.SegmentsHex) > 0 {
		wide, err := segment.WideFingerprintFromHexSegments(spec.SegmentsHex)
		if err != nil {
			return CheckpointOutcome{}, err
		}
		bound := codec.BindWideFingerprint(tensor, wide)
		return CheckpointOutcome{
			ID:              spec.ID,
			TensorSHA256Hex: codec.HexSHA256(bound),
		}, nil
	}
	asm := d.assemblyFor(spec.ID)
	staged := asm.Bytes()
	bound := append(append([]byte(nil), tensor...), staged...)
	return CheckpointOutcome{
		ID:              spec.ID,
		TensorSHA256Hex: codec.HexSHA256(bound),
	}, nil
}
