#include "model/mass.hpp"

void mass_apply(const std::array<double, 3>& v, const std::array<double, 3>& diag,
                std::array<double, 3>& out) {
  for (int i = 0; i < 3; ++i) {
    out[i] = diag[i] * v[i];
  }
}

void mass_solve(const std::array<double, 3>& rhs, const std::array<double, 3>& diag,
                std::array<double, 3>& x) {
  for (int i = 0; i < 3; ++i) {
    x[i] = rhs[i] / diag[i];
  }
}
