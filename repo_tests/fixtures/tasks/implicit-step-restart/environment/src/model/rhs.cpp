#include "model/rhs.hpp"

#include <cmath>

void rhs_eval(double /*t*/, const std::array<double, 3>& y, const RhsParams& p,
              std::array<double, 3>& f) {
  const double y0 = y[0];
  const double y1 = y[1];
  const double y2 = y[2];
  const double mix = y1 * y2;
  f[0] = -p.k0 * y0 + mix;
  f[1] = p.k0 * y0 - mix - p.k1 * y1 * y1 + 0.015 * y0 * y2;
  f[2] = mix + p.k1 * y1 * y1 - p.k2 * y2 + 0.01 * y0 * y1;
}

void rhs_jacobian(const std::array<double, 3>& y, const RhsParams& p,
                  std::array<std::array<double, 3>, 3>& jac) {
  const double y0 = y[0];
  const double y1 = y[1];
  const double y2 = y[2];
  jac[0][0] = -p.k0;
  jac[0][1] = y2;
  jac[0][2] = y1;

  jac[1][0] = p.k0 + 0.015 * y2;
  jac[1][1] = -y2 - 2.0 * p.k1 * y1;
  jac[1][2] = -y1 + 0.015 * y0;

  jac[2][0] = 0.01 * y1;
  jac[2][1] = y2 + 2.0 * p.k1 * y1 + 0.01 * y0;
  jac[2][2] = y1 - p.k2;
}
