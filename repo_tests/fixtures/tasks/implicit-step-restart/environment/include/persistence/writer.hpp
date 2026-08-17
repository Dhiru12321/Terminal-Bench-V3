#pragma once

#include <array>
#include <cstdint>
#include <fstream>
#include <string>

#include "control/error_controller.hpp"
#include "events/localization.hpp"
#include "nonlinear/embedded_driver.hpp"

struct BundlePayload {
  double t{};
  double dt{};
  std::array<double, 3> y{};
  std::uint32_t accepted{};
  std::uint32_t rejected{};
  std::uint32_t accepted_at_snapshot{};
  std::uint32_t stage_index{};
  std::array<double, 3> k1{};
  std::array<double, 3> k2{};
  NewtonPersist newton{};
  double err_prev{};
  double integral_err{};
  EventState event{};
  std::uint32_t after_pi_for_step{0};
};

class BundleWriter {
 public:
  explicit BundleWriter(std::string audit_path) : audit_path_(std::move(audit_path)) {}

  bool write(const std::string& path, std::uint64_t op_sig, const BundlePayload& p);

 private:
  std::string audit_path_;
  void audit_line(const std::string& msg);
};
