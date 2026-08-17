#pragma once

#include <map>
#include <string>

namespace ts {

struct TileChunk {
  int id{0};
  std::map<std::string, std::string> rows;
};

}  // namespace ts
