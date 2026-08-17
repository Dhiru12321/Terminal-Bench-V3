#pragma once

#include "engine/hashable_state.h"

#include <string>

namespace util {

[[nodiscard]] std::string digest_hex_256(const eng::CanonicalProjection& c);

}  // namespace util
