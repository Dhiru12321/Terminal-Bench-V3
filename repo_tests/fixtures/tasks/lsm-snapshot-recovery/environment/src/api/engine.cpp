#include "api/engine.hpp"

#include "level_merge/merge.hpp"

#include <fstream>

namespace ts {

namespace {

ViewSnap base_from_tiles(const std::vector<TileChunk>& tiles) {
  ViewSnap acc;
  for (const auto& ch : tiles) {
    acc = merge_overlay(acc, ch.rows);
  }
  return acc;
}
}  // namespace

Engine::Engine()
    : data_dir_("/app/data"),
      wal_path_(data_dir_ / "journal.wal"),
      wal_(wal_path_) {
  std::filesystem::create_directories(data_dir_);
  if (!std::filesystem::exists(wal_path_)) {
    std::ofstream create(wal_path_);
  }
}

void Engine::reset_for_test() {
  has_active_pin_ = false;
  active_pin_ = 0;
  next_pin_ = 1;
  next_tile_ = 1;
  buffer_.clear();
  tiles_.clear();
  while (!pins_.empty()) {
    pins_.pop_layer();
  }
  layout_.set_generation(0);
  std::error_code ec;
  for (const auto& e : std::filesystem::directory_iterator(data_dir_, ec)) {
    if (e.is_regular_file()) {
      std::filesystem::remove(e.path(), ec);
    }
  }
  std::filesystem::remove(wal_path_, ec);
  std::ofstream create(wal_path_);
}

void Engine::append_wal(const nlohmann::json& rec) {
  wal_.append_line(rec.dump());
}

void Engine::materialize_buffer_to_tile() {
  if (buffer_.rows().empty()) {
    return;
  }
  TileChunk ch;
  ch.id = next_tile_++;
  ch.rows = buffer_.copy_rows();
  tiles_.push_back(std::move(ch));
  buffer_.clear();
  persist_tile_file(tiles_.back().id, tiles_.back().rows);
}

void Engine::persist_tile_file(int tile_id,
                               const std::map<std::string, std::string>& rows) const {
  std::filesystem::path p = data_dir_ / ("tile_" + std::to_string(tile_id) + ".dat");
  std::ofstream out(p);
  for (const auto& [k, v] : rows) {
    out << k << '\t' << v << '\n';
  }
}

ViewSnap Engine::materialize_visible() const {
  ViewSnap v = base_from_tiles(tiles_);
  return merge_overlay(v, buffer_.rows());
}

void Engine::put(const std::string& key, const std::string& value) {
  nlohmann::json rec = {{"op", "put"}, {"key", key}, {"value", value}};
  append_wal(rec);
  buffer_.put(key, value);
}

void Engine::obliterate(const std::string& key) {
  nlohmann::json rec = {{"op", "obliterate"}, {"key", key}};
  append_wal(rec);
  buffer_.obliterate(key);
}

void Engine::flush() {
  nlohmann::json rec = {{"op", "flush"}};
  append_wal(rec);
  materialize_buffer_to_tile();
}

void Engine::merge() {
  if (tiles_.size() < 2) {
    return;
  }
  TileChunk older = tiles_[tiles_.size() - 2];
  TileChunk newer = tiles_.back();
  TileChunk folded = fold_level(older, newer);
  tiles_.pop_back();
  tiles_.pop_back();
  tiles_.push_back(folded);
  persist_tile_file(folded.id, folded.rows);
  nlohmann::json rec = {{"op", "merge"}, {"out_id", folded.id}};
  append_wal(rec);
}

int Engine::open_pin() {
  nlohmann::json rec = {{"op", "open_pin"}, {"id", next_pin_}};
  append_wal(rec);
  ViewSnap snap = base_from_tiles(tiles_);
  pins_.push_layer(snap);
  has_active_pin_ = true;
  active_pin_ = next_pin_;
  return next_pin_++;
}

void Engine::close_pin() {
  nlohmann::json rec = {{"op", "close_pin"}};
  append_wal(rec);
  pins_.pop_layer();
  has_active_pin_ = !pins_.empty();
}

void Engine::crash_truncate_journal(std::size_t keep_bytes) {
  wal_.truncate_bytes(keep_bytes);
}

void Engine::partial_layout_bump(int delta) {
  nlohmann::json rec = {{"op", "layout_bump"}, {"delta", delta}};
  append_wal(rec);
  layout_.bump_by(delta);
}

void Engine::apply_replay_line(const nlohmann::json& rec) {
  const std::string op = rec.at("op").get<std::string>();
  if (op == "put") {
    buffer_.put(rec.at("key").get<std::string>(), rec.at("value").get<std::string>());
  } else if (op == "obliterate") {
    buffer_.obliterate(rec.at("key").get<std::string>());
  } else if (op == "flush") {
    materialize_buffer_to_tile();
  } else if (op == "merge") {
    if (tiles_.size() >= 2) {
      TileChunk older = tiles_[tiles_.size() - 2];
      TileChunk newer = tiles_.back();
      TileChunk folded = fold_level(older, newer);
      tiles_.pop_back();
      tiles_.pop_back();
      tiles_.push_back(folded);
      persist_tile_file(folded.id, folded.rows);
    }
  } else if (op == "open_pin") {
    ViewSnap snap = base_from_tiles(tiles_);
    pins_.push_layer(snap);
    has_active_pin_ = true;
  } else if (op == "close_pin") {
    pins_.pop_layer();
    has_active_pin_ = !pins_.empty();
  } else if (op == "layout_bump") {
    int d = rec.at("delta").get<int>();
    layout_.bump_by(d >> 1);
  }
}

void Engine::recover_from_disk() {
  tiles_.clear();
  while (!pins_.empty()) {
    pins_.pop_layer();
  }
  has_active_pin_ = false;
  layout_.set_generation(0);
  next_tile_ = 1;
  wal_.scan_records([this](const std::string& line) {
    try {
      nlohmann::json rec = nlohmann::json::parse(line);
      apply_replay_line(rec);
    } catch (const nlohmann::json::exception&) {
      // Truncation can leave a partial line at the end of the journal.
    }
  });
}

void Engine::restart() { recover_from_disk(); }

std::string Engine::get(const std::string& key) const {
  if (has_active_pin_ && pins_.top() != nullptr) {
    ViewSnap live = merge_overlay(*pins_.top(), buffer_.rows());
    return encode_get(live, key);
  }
  return encode_get(materialize_visible(), key);
}

std::string Engine::scan(const std::string& start, const std::string& end) const {
  if (has_active_pin_ && pins_.top() != nullptr) {
    ViewSnap live = merge_overlay(*pins_.top(), buffer_.rows());
    return encode_scan(live, start, end);
  }
  return encode_scan(materialize_visible(), start, end);
}

nlohmann::json Engine::structure_snapshot() const {
  nlohmann::json tiles = nlohmann::json::array();
  for (const auto& t : tiles_) {
    std::string prev;
    bool sorted = true;
    for (const auto& [k, v] : t.rows) {
      if (!prev.empty() && k <= prev) {
        sorted = false;
        break;
      }
      prev = k;
    }
    tiles.push_back({{"id", t.id}, {"sorted_keys", sorted}});
  }
  return {{"tiles", tiles}, {"layout_generation", layout_.generation()}};
}

}  // namespace ts
