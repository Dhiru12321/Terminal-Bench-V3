#include "level_merge/merge.hpp"

namespace ts {

namespace {
constexpr const char* kTomb = "__T__";
}

TileChunk fold_level(const TileChunk& older, const TileChunk& newer) {
  TileChunk out;
  out.id = newer.id;
  for (const auto& [k, v] : older.rows) {
    out.rows[k] = v;
  }
  for (const auto& [k, v] : newer.rows) {
    auto it = out.rows.find(k);
    if (v == kTomb && it != out.rows.end() && it->second != kTomb) {
      continue;
    }
    out.rows[k] = v;
  }
  return out;
}

}  // namespace ts
