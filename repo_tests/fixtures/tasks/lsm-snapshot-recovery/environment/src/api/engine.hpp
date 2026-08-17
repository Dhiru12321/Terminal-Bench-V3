#pragma once

#include "buffer/buffer.hpp"
#include "cursor_pin/pin.hpp"
#include "layout_index/layout.hpp"
#include "tile/tile.hpp"
#include "wal_record/wal.hpp"

#include <nlohmann/json.hpp>

#include <filesystem>
#include <string>

namespace ts {

class Engine {
 public:
  Engine();
  void reset_for_test();

  void put(const std::string& key, const std::string& value);
  void obliterate(const std::string& key);
  void flush();
  void merge();
  int open_pin();
  void close_pin();
  void crash_truncate_journal(std::size_t keep_bytes);
  void restart();
  void partial_layout_bump(int delta);

  std::string get(const std::string& key) const;
  std::string scan(const std::string& start, const std::string& end) const;
  nlohmann::json structure_snapshot() const;

  int layout_generation() const { return layout_.generation(); }
  const std::filesystem::path& journal_path() const { return wal_path_; }

 private:
  void append_wal(const nlohmann::json& rec);
  void apply_replay_line(const nlohmann::json& rec);
  void recover_from_disk();
  void persist_tile_file(int tile_id, const std::map<std::string, std::string>& rows) const;
  void materialize_buffer_to_tile();
  ViewSnap materialize_visible() const;

  std::filesystem::path data_dir_;
  std::filesystem::path wal_path_;
  WalJournal wal_;
  BufferSlot buffer_;
  std::vector<TileChunk> tiles_;
  LayoutLedger layout_;
  PinBook pins_;
  int next_pin_{1};
  int next_tile_{1};
  int active_pin_{0};
  bool has_active_pin_{false};
};

}  // namespace ts
