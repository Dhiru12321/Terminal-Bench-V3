#include "replay/io.h"

#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

namespace replay {

void write_blob_file(const std::string& path, const std::vector<std::byte>& data) {
  std::ofstream f(path, std::ios::binary | std::ios::trunc);
  if (!f) {
    throw std::runtime_error("write_blob_file");
  }
  f.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
}

std::vector<std::byte> read_blob_file(const std::string& path) {
  std::ifstream f(path, std::ios::binary);
  if (!f) {
    throw std::runtime_error("read_blob_file");
  }
  const std::string raw((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
  std::vector<std::byte> out;
  out.reserve(raw.size());
  for (unsigned char c : raw) {
    out.push_back(static_cast<std::byte>(c));
  }
  return out;
}

}  // namespace replay
