#pragma once

#include <array>

struct RhsParams {
  double k0{};
  double k1{};
  double k2{};
};

void rhs_eval(double t, const std::array<double, 3>& y, const RhsParams& p,
              std::array<double, 3>& f);

void rhs_jacobian(const std::array<double, 3>& y, const RhsParams& p,
                  std::array<std::array<double, 3>, 3>& jac);
