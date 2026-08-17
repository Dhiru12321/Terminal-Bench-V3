#include "integrator/butcher.hpp"

namespace butcher {

Tableau make_table(double gamma) {
  Tableau t{};
  t.gamma = gamma;
  t.c1 = gamma;
  t.c2 = 1.0;
  t.a11 = gamma;
  t.a21 = 1.0 - gamma;
  t.a22 = gamma;
  t.b1 = 1.0 - gamma;
  t.b2 = gamma;
  t.bhat1 = 0.5;
  t.bhat2 = 0.5;
  return t;
}

}  // namespace butcher
