#pragma once

#include <array>

#include "integrator/butcher.hpp"
#include "model/rhs.hpp"

struct NewtonConfig {
  int max_iter{20};
  double tol{1e-10};
};

struct NewtonPersist {
  int iter_count{0};
  double alpha{1.0};
  std::array<double, 3> k_guess{};
  int had_ls_backoff{0};
};

class EmbeddedDriver {
 public:
  void set_mass_diag(const std::array<double, 3>& d) { mass_diag_ = d; }
  void set_rhs_params(const RhsParams& p) { rhs_ = p; }
  void set_table(const butcher::Tableau& tab) { tab_ = tab; }

  using NewtonHook = bool (*)(int newton_iter, const NewtonPersist& p, void* ctx);

  bool solve_stage(double t0, double h, int stage_index, const std::array<double, 3>& y0,
                   const std::array<double, 3>& k_prev_contrib, double aii,
                   std::array<double, 3>& k_out, NewtonConfig cfg, NewtonPersist& persist,
                   int& newton_iters_out, NewtonHook hook = nullptr, void* hook_ctx = nullptr,
                   bool* hooked_stop = nullptr);

  void reset_counts() { total_iters_ = 0; }
  int total_iters() const { return total_iters_; }

 private:
  std::array<double, 3> mass_diag_{};
  RhsParams rhs_{};
  butcher::Tableau tab_{};
  int total_iters_{0};

  void residual(double t_stage, double h, double aii, const std::array<double, 3>& y0,
                const std::array<double, 3>& k_accum_before, const std::array<double, 3>& k_try,
                std::array<double, 3>& R);

  void form_jacobian(double t_stage, double h, double aii, const std::array<double, 3>& y0,
                     const std::array<double, 3>& k_accum_before, const std::array<double, 3>& k_try,
                     std::array<std::array<double, 3>, 3>& J);
  bool linsolve(const std::array<std::array<double, 3>, 3>& A, const std::array<double, 3>& b,
                std::array<double, 3>& x);
};
