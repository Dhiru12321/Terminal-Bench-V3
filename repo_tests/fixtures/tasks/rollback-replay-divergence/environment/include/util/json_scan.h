#pragma once

#include <cstddef>
#include <map>
#include <string>
#include <vector>

namespace util {

struct JsonValue;

struct JsonValue {
  enum class Kind { Null, Bool, Number, String, Array, Object } kind = Kind::Null;
  bool b = false;
  double num = 0;
  std::string s;
  std::vector<JsonValue> arr;
  std::map<std::string, JsonValue> obj;

  [[nodiscard]] const JsonValue* get(std::string_view key) const;
  [[nodiscard]] const JsonValue& at(std::string_view key) const;
};

// Parses a JSON document (object or array root). Returns null value on failure.
[[nodiscard]] JsonValue parse_json(std::string_view text);

}  // namespace util
