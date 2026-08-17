#pragma once

#include <string>
#include <vector>

namespace replay {

void write_blob_file(const std::string& path, const std::vector<std::byte>& data);
[[nodiscard]] std::vector<std::byte> read_blob_file(const std::string& path);

}  // namespace replay
