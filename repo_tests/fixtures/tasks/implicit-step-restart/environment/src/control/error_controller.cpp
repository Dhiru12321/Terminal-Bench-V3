#include "control/error_controller.hpp"

#include <algorithm>
#include <cmath>

void ErrorController::record_error(double err) { err_prev = err; }

double ErrorController::suggest_scale(double err, double tol) const {
  const double r = std::max(err / std::max(tol, 1e-30), 1e-12);
  double fac = safety * std::pow(1.0 / r, 0.38);
  const double ratio = err_prev / std::max(err, 1e-30);
  fac *= std::pow(ratio, beta_pi);
  fac = std::clamp(fac, facmin, facmax);
  return fac;
}

void ErrorController::pi_update(double err, double tol) {
  const double ehat = err / std::max(tol, 1e-30);
  integral_err += (ehat - 1.0);
  err_prev = err;
}
