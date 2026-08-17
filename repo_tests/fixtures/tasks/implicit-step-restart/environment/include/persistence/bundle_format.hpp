#pragma once

#include <cstdint>
#include <string>

std::uint32_t bundle_magic();

std::uint32_t bundle_layout_version();

std::uint64_t fnv1a64(const std::string& s);
