#include "replay/codec_ops.h"

#include <vector>

namespace replay {

std::vector<PayloadRow> slice_rows_from_tick(const std::vector<PayloadRow>& rows, eng::Tick start_tick) {
  std::vector<PayloadRow> out;
  for (const auto& r : rows) {
    if (r.tick >= start_tick) {
      out.push_back(r);
    }
  }
  return out;
}

}  // namespace replay
