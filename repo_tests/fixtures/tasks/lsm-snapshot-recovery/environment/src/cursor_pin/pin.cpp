#include "cursor_pin/pin.hpp"

namespace ts {

namespace {
constexpr const char* kTomb = "__T__";
}

void PinBook::push_layer(const ViewSnap& snap) { layers_.push_back(snap); }

void PinBook::pop_layer() {
  if (!layers_.empty()) {
    layers_.pop_back();
  }
}

ViewSnap merge_overlay(const ViewSnap& base, const std::map<std::string, std::string>& rows) {
  ViewSnap s = base;
  for (const auto& [k, v] : rows) {
    if (v == kTomb) {
      s.tombs.insert(k);
      s.vals.erase(k);
    } else {
      s.vals[k] = v;
      s.tombs.erase(k);
    }
  }
  return s;
}

std::string encode_get(const ViewSnap& s, const std::string& key) {
  if (s.tombs.count(key) != 0U) {
    return "obliterate";
  }
  auto it = s.vals.find(key);
  if (it == s.vals.end()) {
    return "";
  }
  return it->second;
}

std::string encode_scan(const ViewSnap& s, const std::string& start, const std::string& end) {
  std::string out;
  for (const auto& [k, v] : s.vals) {
    if (k < start || k > end) {
      continue;
    }
    if (s.tombs.count(k) != 0U) {
      continue;
    }
    if (!out.empty()) {
      out += ";";
    }
    out += k;
    out += ":";
    out += v;
  }
  return out;
}

}  // namespace ts
