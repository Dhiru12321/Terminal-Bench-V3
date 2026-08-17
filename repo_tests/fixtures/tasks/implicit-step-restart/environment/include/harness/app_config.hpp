#pragma once

#include <array>
#include <string>

#include "model/rhs.hpp"

struct AppConfig {
  double rtol{1e-5};
  double atol{1e-8};
  double safety{0.9};
  double facmin{0.25};
  double facmax{2.0};
  double alpha_pi{0.7};
  double beta_pi{0.04};

  int newton_max{24};
  double newton_tol{1e-11};

  double t_start{0.0};
  double t_end{1.0};
  double initial_dt{1e-4};
  std::array<double, 3> y0{};

  RhsParams model{};
  std::array<double, 3> mass_diag{};
  double stability_extra_damping{0.0};
  double butcher_gamma{0.2928932188134524};

  int event_component{0};
  double event_target{0.5};

  std::string work_dir{"/app/work"};
  std::string data_path{"/app/data/default.toml"};
};

bool load_app_config(const std::string& path, AppConfig& cfg);

std::string operator_fingerprint_string(const AppConfig& cfg);
