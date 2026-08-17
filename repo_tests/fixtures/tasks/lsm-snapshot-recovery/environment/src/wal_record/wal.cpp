#include "wal_record/wal.hpp"

#include <fstream>
#include <sstream>

namespace ts {

WalJournal::WalJournal(std::filesystem::path path) : path_(std::move(path)) {}

void WalJournal::append_line(const std::string& line) {
  std::ofstream out(path_, std::ios::app);
  out << line << '\n';
}

void WalJournal::truncate_bytes(std::size_t keep) {
  std::ifstream in(path_);
  std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
  if (content.size() > keep) {
    content.resize(keep);
  }
  std::ofstream out(path_, std::ios::trunc);
  out << content;
}

void WalJournal::scan_records(const std::function<void(const std::string&)>& sink) const {
  std::ifstream in(path_);
  std::string line;
  while (std::getline(in, line)) {
    if (!line.empty()) {
      sink(line);
    }
  }
}

}  // namespace ts
