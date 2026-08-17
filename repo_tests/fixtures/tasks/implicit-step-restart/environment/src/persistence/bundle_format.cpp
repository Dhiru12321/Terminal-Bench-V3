#include "persistence/bundle_format.hpp"

#include <string>

std::uint32_t bundle_magic() { return 0x31454d44u; }

std::uint32_t bundle_layout_version() { return 5u; }

std::uint64_t fnv1a64(const std::string& s) {
  std::uint64_t h = 14695981039346656037ull;
  for (unsigned char c : s) {
    h ^= static_cast<std::uint64_t>(c);
    h *= 1099511628211ull;
  }
  return h;
}
