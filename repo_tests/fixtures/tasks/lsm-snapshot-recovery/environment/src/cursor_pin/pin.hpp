#pragma once

#include <map>
#include <set>
#include <string>
#include <vector>

namespace ts {

struct ViewSnap {
  std::map<std::string, std::string> vals;
  std::set<std::string> tombs;
};

class PinBook {
 public:
  void push_layer(const ViewSnap& snap);
  void pop_layer();
  bool empty() const { return layers_.empty(); }
  const ViewSnap* top() const { return layers_.empty() ? nullptr : &layers_.back(); }

 private:
  std::vector<ViewSnap> layers_;
};

std::string encode_get(const ViewSnap& s, const std::string& key);
std::string encode_scan(const ViewSnap& s, const std::string& start, const std::string& end);

ViewSnap merge_overlay(const ViewSnap& base, const std::map<std::string, std::string>& rows);

}  // namespace ts
