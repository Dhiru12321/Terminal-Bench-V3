#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace util {

void append_u32_le(std::vector<std::uint8_t>& b, std::uint32_t v);
void append_u64_le(std::vector<std::uint8_t>& b, std::uint64_t v);
[[nodiscard]] std::uint32_t read_u32_le(const std::vector<std::uint8_t>& b, std::size_t& off);
[[nodiscard]] std::uint64_t read_u64_le(const std::vector<std::uint8_t>& b, std::size_t& off);

}  // namespace util
