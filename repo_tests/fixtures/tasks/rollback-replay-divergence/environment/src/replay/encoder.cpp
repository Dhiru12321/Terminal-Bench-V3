#include "replay/codec_ops.h"
#include "replay/header.h"

#include "util/buffer.h"

#include <cstring>
#include <vector>

namespace replay {

static void append_i8(std::vector<std::uint8_t>& b, std::int8_t v) {
  b.push_back(static_cast<std::uint8_t>(v));
}

std::vector<std::uint8_t> encode_rows_revision1(const std::vector<PayloadRow>& rows) {
  std::vector<std::uint8_t> b;
  util::append_u32_le(b, static_cast<std::uint32_t>(rows.size()));
  for (const auto& r : rows) {
    util::append_u32_le(b, static_cast<std::uint32_t>(r.tick));
    append_i8(b, r.p0);
    append_i8(b, r.p1);
  }
  return b;
}

std::vector<std::uint8_t> encode_rows_revision2(const std::vector<PayloadRow>& rows) {
  std::vector<std::uint8_t> b;
  util::append_u32_le(b, static_cast<std::uint32_t>(rows.size()));
  for (const auto& r : rows) {
    util::append_u32_le(b, static_cast<std::uint32_t>(r.tick));
    append_i8(b, r.p0);
    append_i8(b, r.p1);
    b.push_back(r.mask);
  }
  return b;
}

std::vector<std::byte> encode_replay_blob(std::uint64_t seed, std::uint32_t format_revision,
                                          const std::vector<PayloadRow>& rows) {
  const std::vector<std::uint8_t> body = encode_rows_revision2(rows);
  replay::ContainerHeader hdr{};
  hdr.seed = seed;
  hdr.format_revision = format_revision;
  hdr.tick_span = static_cast<std::uint32_t>(rows.size());
  std::vector<std::byte> out(sizeof(hdr) + body.size());
  std::memcpy(out.data(), &hdr, sizeof(hdr));
  std::memcpy(out.data() + sizeof(hdr), body.data(), body.size());
  return out;
}

std::vector<std::byte> encode_replay_blob_revision1(std::uint64_t seed, const std::vector<PayloadRow>& rows) {
  const std::vector<std::uint8_t> body = encode_rows_revision1(rows);
  replay::ContainerHeader hdr{};
  hdr.seed = seed;
  hdr.format_revision = 1;
  hdr.tick_span = static_cast<std::uint32_t>(rows.size());
  std::vector<std::byte> out(sizeof(hdr) + body.size());
  std::memcpy(out.data(), &hdr, sizeof(hdr));
  std::memcpy(out.data() + sizeof(hdr), body.data(), body.size());
  return out;
}

}  // namespace replay
