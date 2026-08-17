#include "util/buffer.h"

#include <vector>

namespace util {

void append_u32_le(std::vector<std::uint8_t>& b, std::uint32_t v) {
  b.push_back(static_cast<std::uint8_t>(v & 0xFF));
  b.push_back(static_cast<std::uint8_t>((v >> 8) & 0xFF));
  b.push_back(static_cast<std::uint8_t>((v >> 16) & 0xFF));
  b.push_back(static_cast<std::uint8_t>((v >> 24) & 0xFF));
}

void append_u64_le(std::vector<std::uint8_t>& b, std::uint64_t v) {
  for (int i = 0; i < 8; ++i) {
    b.push_back(static_cast<std::uint8_t>((v >> (8 * i)) & 0xFF));
  }
}

std::uint32_t read_u32_le(const std::vector<std::uint8_t>& b, std::size_t& off) {
  std::uint32_t v = 0;
  for (int i = 0; i < 4; ++i) {
    v |= static_cast<std::uint32_t>(b.at(off + i)) << (8 * i);
  }
  off += 4;
  return v;
}

std::uint64_t read_u64_le(const std::vector<std::uint8_t>& b, std::size_t& off) {
  std::uint64_t v = 0;
  for (int i = 0; i < 8; ++i) {
    v |= static_cast<std::uint64_t>(b.at(off + i)) << (8 * i);
  }
  off += 8;
  return v;
}

}  // namespace util
