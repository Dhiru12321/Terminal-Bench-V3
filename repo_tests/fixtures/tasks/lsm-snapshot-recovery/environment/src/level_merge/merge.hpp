#pragma once

#include "tile/tile.hpp"

namespace ts {

TileChunk fold_level(const TileChunk& older, const TileChunk& newer);

}  // namespace ts
