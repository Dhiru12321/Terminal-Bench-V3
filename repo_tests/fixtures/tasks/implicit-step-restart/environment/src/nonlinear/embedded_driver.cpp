#include "nonlinear/embedded_driver.hpp"

#include <algorithm>
#include <cmath>

#include "model/mass.hpp"

void EmbeddedDriver::residual(double t_stage, double h, double aii, const std::array<double, 3>& y0,
                              const std::array<double, 3>& k_accum_before,
                              const std::array<double, 3>& k_try, std::array<double, 3>& R) {
  std::array<double, 3> Y{};
  for (int i = 0; i < 3; ++i) {
    Y[i] = y0[i] + h * (k_accum_before[i] + aii * k_try[i]);
  }
  std::array<double, 3> f{};
  rhs_eval(t_stage, Y, rhs_, f);
  std::array<double, 3> Mk{};
  mass_apply(k_try, mass_diag_, Mk);
  for (int i = 0; i < 3; ++i) {
    R[i] = Mk[i] - f[i];
  }
}

void EmbeddedDriver::form_jacobian(double /*t_stage*/, double h, double aii,
                                   const std::array<double, 3>& y0,
                                   const std::array<double, 3>& k_accum_before,
                                   const std::array<double, 3>& k_try,
                                   std::array<std::array<double, 3>, 3>& J) {
  std::array<double, 3> Y{};
  for (int i = 0; i < 3; ++i) {
    Y[i] = y0[i] + h * (k_accum_before[i] + aii * k_try[i]);
  }
  std::array<std::array<double, 3>, 3> Jf{};
  rhs_jacobian(Y, rhs_, Jf);
  for (int r = 0; r < 3; ++r) {
    for (int c = 0; c < 3; ++c) {
      J[r][c] = -h * aii * Jf[r][c];
    }
    J[r][r] += mass_diag_[r];
  }
}

bool EmbeddedDriver::linsolve(const std::array<std::array<double, 3>, 3>& A,
                              const std::array<double, 3>& b, std::array<double, 3>& x) {
  double M[3][4] = {{A[0][0], A[0][1], A[0][2], -b[0]},
                    {A[1][0], A[1][1], A[1][2], -b[1]},
                    {A[2][0], A[2][1], A[2][2], -b[2]}};
  for (int col = 0; col < 3; ++col) {
    int piv = col;
    for (int r = col + 1; r < 3; ++r) {
      if (std::fabs(M[r][col]) > std::fabs(M[piv][col])) {
        piv = r;
      }
    }
    if (std::fabs(M[piv][col]) < 1e-18) {
      return false;
    }
    if (piv != col) {
      for (int c = col; c < 4; ++c) {
        std::swap(M[col][c], M[piv][c]);
      }
    }
    const double div = M[col][col];
    for (int c = col; c < 4; ++c) {
      M[col][c] /= div;
    }
    for (int r = 0; r < 3; ++r) {
      if (r == col) {
        continue;
      }
      const double f = M[r][col];
      for (int c = col; c < 4; ++c) {
        M[r][c] -= f * M[col][c];
      }
    }
  }
  x[0] = M[0][3];
  x[1] = M[1][3];
  x[2] = M[2][3];
  return true;
}

bool EmbeddedDriver::solve_stage(double t0, double h, int stage_index, const std::array<double, 3>& y0,
                                 const std::array<double, 3>& k_prev_contrib, double aii,
                                 std::array<double, 3>& k_out, NewtonConfig cfg, NewtonPersist& persist,
                                 int& newton_iters_out, NewtonHook hook, void* hook_ctx, bool* hooked_stop) {
  const double c = (stage_index == 0) ? tab_.c1 : tab_.c2;
  const double t_stage = t0 + c * h;
  std::array<double, 3> k = persist.k_guess;
  if (persist.iter_count < 0) {
    k = {};
  }
  newton_iters_out = 0;

  auto eval_norm = [&](const std::array<double, 3>& kk) {
    std::array<double, 3> RR{};
    residual(t_stage, h, aii, y0, k_prev_contrib, kk, RR);
    double s = 0.0;
    for (double v : RR) {
      s += v * v;
    }
    return std::sqrt(s);
  };

  for (int it = 0; it < cfg.max_iter; ++it) {
    persist.iter_count = it;
    if (hook && hook(it, persist, hook_ctx)) {
      if (hooked_stop) {
        *hooked_stop = true;
      }
      newton_iters_out = it;
      total_iters_ += it;
      return false;
    }
    std::array<double, 3> R{};
    residual(t_stage, h, aii, y0, k_prev_contrib, k, R);
    double nr = eval_norm(k);
    if (nr < cfg.tol) {
      k_out = k;
      persist.k_guess = k;
      newton_iters_out = it + 1;
      total_iters_ += newton_iters_out;
      return true;
    }
    std::array<std::array<double, 3>, 3> J{};
    form_jacobian(t_stage, h, aii, y0, k_prev_contrib, k, J);
    std::array<double, 3> delta{};
    if (!linsolve(J, R, delta)) {
      return false;
    }
    double alpha = persist.alpha;
    if (alpha <= 0.0 || alpha > 1.0) {
      alpha = 1.0;
    }
    const double n0 = nr;
    std::array<double, 3> trial{};
    bool stepped = false;
    for (int ls = 0; ls < 14; ++ls) {
      for (int i = 0; i < 3; ++i) {
        trial[i] = k[i] + alpha * delta[i];
      }
      const double n1 = eval_norm(trial);
      if (n1 <= n0 * 1.0002 || alpha <= 1.01e-4) {
        if (alpha < 1.0 - 1e-9) {
          persist.had_ls_backoff = 1;
        }
        k = trial;
        persist.alpha = alpha;
        stepped = true;
        break;
      }
      alpha *= 0.5;
      persist.had_ls_backoff = 1;
    }
    if (!stepped) {
      return false;
    }
    newton_iters_out = it + 1;
  }
  total_iters_ += newton_iters_out;
  return false;
}
