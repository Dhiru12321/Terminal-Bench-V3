#include "replay/version.h"

namespace replay {

std::uint32_t reader_accepts_lowest_revision() {
  return 1;
}

std::uint32_t writer_current_revision() {
  return 2;
}

}  // namespace replay
