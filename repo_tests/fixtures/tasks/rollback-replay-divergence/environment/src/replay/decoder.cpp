#include "replay/codec_ops.h"
#include "replay/header.h"

#include "util/buffer.h"

#include <cstring>
#include <stdexcept>
#include <string_view>

namespace replay {

ParsedReplayFile parse_replay_bytes(std::string_view raw_bytes) {
  if (raw_bytes.size() < sizeof(ContainerHeader)) {
    throw std::runtime_error("truncated replay");
  }
  ContainerHeader hdr{};
  std::memcpy(&hdr, raw_bytes.data(), sizeof(hdr));
  if (hdr.magic != 0x524C4244u) {
    throw std::runtime_error("bad replay magic");
  }
  ParsedReplayFile out;
  out.seed = hdr.seed;
  out.format_revision = hdr.format_revision;
  out.payload.assign(raw_bytes.begin() + static_cast<std::ptrdiff_t>(sizeof(hdr)),
                       raw_bytes.end());
  return out;
}

std::vector<PayloadRow> decode_rows(std::uint32_t format_revision, const std::vector<std::uint8_t>& body) {
  std::size_t off = 0;
  const std::uint32_t n = util::read_u32_le(body, off);
  std::vector<PayloadRow> rows;
  rows.reserve(n);
  for (std::uint32_t i = 0; i < n; ++i) {
    if (off + 4 > body.size()) {
      throw std::runtime_error("truncated row tick");
    }
    PayloadRow r;
    r.tick = static_cast<eng::Tick>(util::read_u32_le(body, off));
    if (off + 2 > body.size()) {
      throw std::runtime_error("truncated row dx");
    }
    r.p0 = static_cast<std::int8_t>(body.at(off++));
    r.p1 = static_cast<std::int8_t>(body.at(off++));
    if (format_revision >= 2) {
      if (off >= body.size()) {
        throw std::runtime_error("truncated mask");
      }
      r.mask = body.at(off++);
    } else {
      r.mask = 3;
    }
    rows.push_back(r);
  }
  return rows;
}

std::vector<sim::TickInputs> rows_to_inputs(const std::vector<PayloadRow>& rows) {
  std::vector<sim::TickInputs> out;
  out.reserve(rows.size());
  for (const auto& r : rows) {
    sim::TickInputs tin{};
    tin.tick = r.tick;
    const bool have0 = (r.mask & 1u) != 0;
    const bool have1 = (r.mask & 2u) != 0;
#if TB_REEXEC_MODE == 1
    tin.remote_slot_present[0] = true;
    tin.remote_slot_present[1] = true;
    tin.staged[0].dx = have0 ? r.p0 : static_cast<std::int8_t>(0);
    tin.staged[1].dx = have1 ? r.p1 : static_cast<std::int8_t>(0);
#else
    tin.remote_slot_present[0] = true;
    tin.remote_slot_present[1] = true;
    tin.staged[0].dx = have0 ? r.p0 : static_cast<std::int8_t>(0);
    tin.staged[1].dx = have1 ? r.p1 : static_cast<std::int8_t>(0);
#endif
    out.push_back(tin);
  }
  return out;
}

}  // namespace replay
