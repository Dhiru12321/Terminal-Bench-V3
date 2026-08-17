#include "util/digest.h"

#include "engine/hashable_state.h"

#include <array>
#include <cstdint>
#include <iomanip>
#include <sstream>
#include <string>

namespace util {

[[nodiscard]] std::string digest_hex_256(const eng::CanonicalProjection& c) {
  const std::string line = c.pack_line();
  std::uint64_t h[4] = {14695981039346656037ULL, 1099511628211ULL, 0xD6E8FEB866B1B965ULL, 0xC6A4A7935BD1E995ULL};
  for (unsigned char ch : line) {
    h[0] ^= ch;
    h[0] *= 1099511628211ULL;
    h[1] ^= static_cast<std::uint64_t>(ch) << 8;
    h[1] *= 0x100000001B3ULL;
    h[2] ^= h[0] + h[1];
    h[3] ^= h[2] >> 17;
  }
  h[0] ^= c.tick;
  h[1] ^= c.entropy_fold;
  std::ostringstream out;
  out << std::hex << std::setfill('0');
  for (std::uint64_t v : h) {
    out << std::setw(16) << v;
  }
  return out.str();
}

}  // namespace util
