#pragma once

#include "sim/command_log.h"

#include <string>
#include <tuple>
#include <vector>

namespace harness {

using TraceBundleLine = std::tuple<std::string, sim::LoggedTick>;

void write_trace_bundle(const std::string& path, const std::vector<TraceBundleLine>& lines);

}  // namespace harness
