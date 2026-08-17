#pragma once

namespace butcher {

// Two-stage SDIRK with fixed diagonal gamma (embedded pair uses same stages).
struct Tableau {
  double gamma{};
  double c1{};
  double c2{};
  double a11{};
  double a21{};
  double a22{};
  double b1{};
  double b2{};
  double bhat1{};
  double bhat2{};
};

Tableau make_table(double gamma);

}  // namespace butcher
