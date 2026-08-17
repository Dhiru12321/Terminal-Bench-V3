#pragma once

#include <filesystem>
#include <functional>
#include <string>
#include <vector>

namespace ts {

class WalJournal {
 public:
  explicit WalJournal(std::filesystem::path path);
  void append_line(const std::string& line);
  void truncate_bytes(std::size_t keep);
  void scan_records(const std::function<void(const std::string&)>& sink) const;

 private:
  std::filesystem::path path_;
};

}  // namespace ts
