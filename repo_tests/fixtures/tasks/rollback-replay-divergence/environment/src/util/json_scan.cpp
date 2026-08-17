#include "util/json_scan.h"

#include <cctype>
#include <stdexcept>
#include <string>

namespace util {

static void skip_ws(std::string_view& s, std::size_t& i) {
  while (i < s.size() && std::isspace(static_cast<unsigned char>(s[i]))) {
    ++i;
  }
}

static std::string parse_string(std::string_view s, std::size_t& i) {
  if (i >= s.size() || s[i] != '"') {
    return {};
  }
  ++i;
  std::string out;
  while (i < s.size() && s[i] != '"') {
    if (s[i] == '\\' && i + 1 < s.size()) {
      ++i;
      out.push_back(s[i]);
    } else {
      out.push_back(s[i]);
    }
    ++i;
  }
  if (i < s.size() && s[i] == '"') {
    ++i;
  }
  return out;
}

static double parse_number(std::string_view s, std::size_t& i) {
  std::size_t start = i;
  while (i < s.size() && (std::isdigit(static_cast<unsigned char>(s[i])) || s[i] == '-' || s[i] == '+' ||
                          s[i] == '.' || s[i] == 'e' || s[i] == 'E')) {
    ++i;
  }
  const std::string_view tok = s.substr(start, i - start);
  return std::stod(std::string(tok));
}

static JsonValue parse_value(std::string_view s, std::size_t& i);

static JsonValue parse_array(std::string_view s, std::size_t& i) {
  JsonValue a;
  a.kind = JsonValue::Kind::Array;
  ++i;  // '['
  skip_ws(s, i);
  if (i < s.size() && s[i] == ']') {
    ++i;
    return a;
  }
  while (i < s.size()) {
    a.arr.push_back(parse_value(s, i));
    skip_ws(s, i);
    if (i < s.size() && s[i] == ',') {
      ++i;
      skip_ws(s, i);
      continue;
    }
    break;
  }
  if (i < s.size() && s[i] == ']') {
    ++i;
  }
  return a;
}

static JsonValue parse_object_contents(std::string_view s, std::size_t& i) {
  JsonValue o;
  o.kind = JsonValue::Kind::Object;
  ++i;  // '{'
  skip_ws(s, i);
  if (i < s.size() && s[i] == '}') {
    ++i;
    return o;
  }
  while (i < s.size()) {
    skip_ws(s, i);
    const std::string key = parse_string(s, i);
    skip_ws(s, i);
    if (i < s.size() && s[i] == ':') {
      ++i;
    }
    skip_ws(s, i);
    o.obj[key] = parse_value(s, i);
    skip_ws(s, i);
    if (i < s.size() && s[i] == ',') {
      ++i;
      skip_ws(s, i);
      continue;
    }
    break;
  }
  if (i < s.size() && s[i] == '}') {
    ++i;
  }
  return o;
}

static JsonValue parse_value(std::string_view s, std::size_t& i) {
  skip_ws(s, i);
  if (i >= s.size()) {
    return {};
  }
  if (s[i] == '{') {
    return parse_object_contents(s, i);
  }
  if (s[i] == '[') {
    return parse_array(s, i);
  }
  if (s[i] == '"') {
    JsonValue v;
    v.kind = JsonValue::Kind::String;
    v.s = parse_string(s, i);
    return v;
  }
  if (s.substr(i, 4) == "true") {
    JsonValue v;
    v.kind = JsonValue::Kind::Bool;
    v.b = true;
    i += 4;
    return v;
  }
  if (s.substr(i, 5) == "false") {
    JsonValue v;
    v.kind = JsonValue::Kind::Bool;
    v.b = false;
    i += 5;
    return v;
  }
  if (s.substr(i, 4) == "null") {
    JsonValue v;
    v.kind = JsonValue::Kind::Null;
    i += 4;
    return v;
  }
  JsonValue v;
  v.kind = JsonValue::Kind::Number;
  v.num = parse_number(s, i);
  return v;
}

JsonValue parse_json(std::string_view text) {
  std::size_t i = 0;
  return parse_value(text, i);
}

const JsonValue* JsonValue::get(std::string_view key) const {
  if (kind != Kind::Object) {
    return nullptr;
  }
  const auto it = obj.find(std::string(key));
  if (it == obj.end()) {
    return nullptr;
  }
  return &it->second;
}

const JsonValue& JsonValue::at(std::string_view key) const {
  const JsonValue* p = get(key);
  if (!p) {
    throw std::out_of_range("json key");
  }
  return *p;
}

}  // namespace util
