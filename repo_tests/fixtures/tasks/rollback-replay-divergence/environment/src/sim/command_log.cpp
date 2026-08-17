#include "sim/command_log.h"

#include <sstream>

namespace sim {

void CommandLog::append(const LoggedTick& row) {
  rows_.push_back(row);
}

std::string CommandLog::tail_projection(std::size_t last_n) const {
  if (rows_.empty()) {
    return "";
  }
  const std::size_t start = rows_.size() > last_n ? rows_.size() - last_n : 0;
  std::ostringstream o;
  for (std::size_t i = start; i < rows_.size(); ++i) {
    const auto& r = rows_[i];
    o << r.tick << ':' << static_cast<int>(r.merged_dx[0]) << ',' << static_cast<int>(r.merged_dx[1]) << ';'
      << r.positions[0] << ',' << r.positions[1] << '|';
  }
  return o.str();
}

}  // namespace sim
