#include "net/transport.h"

#include <cstring>
#include <string_view>
#include <vector>

namespace net {

std::vector<std::byte> encode_frame(const FramedTick& ft) {
  net::FrameHeader hdr{};
  hdr.magic = kFrameMagic;
  hdr.revision = 2;
  hdr.tick = static_cast<std::uint32_t>(ft.tick);
  hdr.byte_length = 3;
  std::vector<std::byte> out(sizeof(FrameHeader) + 3);
  std::memcpy(out.data(), &hdr, sizeof(hdr));
  std::memcpy(out.data() + sizeof(FrameHeader), &ft.p0, 1);
  std::memcpy(out.data() + sizeof(FrameHeader) + 1, &ft.p1, 1);
  std::memcpy(out.data() + sizeof(FrameHeader) + 2, &ft.presence, 1);
  return out;
}

bool decode_frame(std::string_view raw, FramedTick& out) {
  if (raw.size() < sizeof(FrameHeader) + 3) {
    return false;
  }
  FrameHeader hdr{};
  std::memcpy(&hdr, raw.data(), sizeof(hdr));
  if (hdr.magic != kFrameMagic) {
    return false;
  }
  out.tick = static_cast<eng::Tick>(hdr.tick);
  std::memcpy(&out.p0, raw.data() + sizeof(FrameHeader), 1);
  std::memcpy(&out.p1, raw.data() + sizeof(FrameHeader) + 1, 1);
  std::memcpy(&out.presence, raw.data() + sizeof(FrameHeader) + 2, 1);
  return true;
}

}  // namespace net
