#include "harness/trace.h"

#include <fstream>

namespace harness {

void write_trace_bundle(const std::string& path, const std::vector<TraceBundleLine>& lines) {
  std::ofstream out(path, std::ios::binary | std::ios::trunc);
  for (const auto& item : lines) {
    const auto& sid = std::get<0>(item);
    const auto& row = std::get<1>(item);
    out << "{\"scenario_id\":\"" << sid << "\",\"tick\":" << row.tick << ",\"merged_dx\":["
        << static_cast<int>(row.merged_dx[0]) << "," << static_cast<int>(row.merged_dx[1]) << "]"
        << ",\"positions\":[" << row.positions[0] << "," << row.positions[1] << "]"
        << ",\"entropy_mix\":" << row.entropy_mix << "}\n";
  }
}

}  // namespace harness
