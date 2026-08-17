#pragma once

#include <map>
#include <string>

namespace ts {

class BufferSlot {
 public:
  void put(const std::string& key, const std::string& value);
  void obliterate(const std::string& key);
  void clear() { rows_.clear(); }
  const std::map<std::string, std::string>& rows() const { return rows_; }
  std::map<std::string, std::string> copy_rows() const { return rows_; }

 private:
  static constexpr const char* kTomb = "__T__";
  std::map<std::string, std::string> rows_;
};

}  // namespace ts
