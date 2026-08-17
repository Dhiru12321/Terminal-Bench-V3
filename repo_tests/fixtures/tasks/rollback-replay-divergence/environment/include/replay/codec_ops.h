#pragma once

#include "engine/types.h"
#include "sim/input_stage.h"

#include <cstdint>
#include <string_view>
#include <vector>

namespace replay {

struct PayloadRow {
  eng::Tick tick = 0;
  std::int8_t p0 = 0;
  std::int8_t p1 = 0;
  std::uint8_t mask = 3;
};

struct ParsedReplayFile {
  std::uint64_t seed = 0;
  std::uint32_t format_revision = 0;
  std::vector<std::uint8_t> payload;
};

[[nodiscard]] std::vector<std::uint8_t> encode_rows_revision1(const std::vector<PayloadRow>& rows);
[[nodiscard]] std::vector<std::uint8_t> encode_rows_revision2(const std::vector<PayloadRow>& rows);
[[nodiscard]] std::vector<std::byte> encode_replay_blob(std::uint64_t seed, std::uint32_t format_revision,
                                                        const std::vector<PayloadRow>& rows);
[[nodiscard]] std::vector<std::byte> encode_replay_blob_revision1(std::uint64_t seed,
                                                                   const std::vector<PayloadRow>& rows);
[[nodiscard]] ParsedReplayFile parse_replay_bytes(std::string_view raw_bytes);
[[nodiscard]] std::vector<PayloadRow> decode_rows(std::uint32_t format_revision,
                                                    const std::vector<std::uint8_t>& body);
[[nodiscard]] std::vector<sim::TickInputs> rows_to_inputs(const std::vector<PayloadRow>& rows);
[[nodiscard]] std::vector<PayloadRow> slice_rows_from_tick(const std::vector<PayloadRow>& rows,
                                                            eng::Tick start_tick);

}  // namespace replay
