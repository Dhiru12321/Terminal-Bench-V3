#pragma once

struct ErrorController {
  double err_prev{1.0};
  double integral_err{0.0};
  double alpha_pi{0.7};
  double beta_pi{0.04};
  double safety{0.9};
  double facmin{0.25};
  double facmax{2.0};

  void record_error(double err);
  double suggest_scale(double err, double tol) const;
  void pi_update(double err, double tol);
};
