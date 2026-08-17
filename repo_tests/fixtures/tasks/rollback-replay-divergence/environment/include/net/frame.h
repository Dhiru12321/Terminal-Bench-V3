#pragma once

#include <cstddef>
#include <cstdint>

namespace net {

constexpr std::uint32_t kFrameMagic = 0x4E504B54;  // NPKT

#pragma pack(push, 1)
struct FrameHeader {
  std::uint32_t magic = kFrameMagic;
  std::uint16_t revision = 2;
  std::uint16_t byte_length = 0;
  std::uint32_t tick = 0;
};
#pragma pack(pop)

constexpr std::size_t kFrameHeaderBytes = sizeof(FrameHeader);

}  // namespace net
