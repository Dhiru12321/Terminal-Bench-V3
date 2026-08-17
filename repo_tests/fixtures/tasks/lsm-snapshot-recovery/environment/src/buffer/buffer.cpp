#include "buffer/buffer.hpp"

namespace ts {

void BufferSlot::put(const std::string& key, const std::string& value) { rows_[key] = value; }

void BufferSlot::obliterate(const std::string& key) { rows_[key] = kTomb; }

}  // namespace ts
