#pragma once

#include "net/frame.h"
#include "net/session.h"

#include <cstddef>
#include <string_view>
#include <vector>

namespace net {

[[nodiscard]] std::vector<std::byte> encode_frame(const FramedTick& ft);
[[nodiscard]] bool decode_frame(std::string_view raw, FramedTick& out);

}  // namespace net
