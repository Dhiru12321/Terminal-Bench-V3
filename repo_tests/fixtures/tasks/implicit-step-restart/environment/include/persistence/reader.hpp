#pragma once

#include <cstdint>
#include <string>

#include "persistence/writer.hpp"

class BundleReader {
 public:
  explicit BundleReader(std::string audit_path) : audit_path_(std::move(audit_path)) {}

  bool try_load(const std::string& path, std::uint64_t expected_sig, BundlePayload& out,
                std::string& reason);

 private:
  std::string audit_path_;
  void audit_line(const std::string& msg);
};
