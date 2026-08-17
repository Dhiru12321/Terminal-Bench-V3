#pragma once

#include <cstdint>

namespace replay {

[[nodiscard]] std::uint32_t reader_accepts_lowest_revision();
[[nodiscard]] std::uint32_t writer_current_revision();

}  // namespace replay
