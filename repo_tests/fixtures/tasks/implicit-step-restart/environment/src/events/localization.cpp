#include "events/localization.hpp"

#include <cmath>

double EventLocalization::g_value(double t, const std::array<double, 3>& y) const {
  const double v = y[static_cast<std::size_t>(component_)];
  return v - target_ + 1e-6 * t;
}

void EventLocalization::begin_bracket(double t0, const std::array<double, 3>& y0, double t1,
                                      const std::array<double, 3>& y1, EventState& st) {
  st.active = true;
  st.locked = false;
  st.t_lo = t0;
  st.t_hi = t1;
  st.y_lo = y0;
  st.y_hi = y1;
  st.g_lo = g_value(t0, y0);
  st.g_hi = g_value(t1, y1);
  st.shrink_pass = 0;
}

void EventLocalization::shrink(double t_mid, const std::array<double, 3>& y_mid, EventState& st) {
  st.shrink_pass += 1;
  const double g_mid = g_value(t_mid, y_mid);
  if (st.g_lo * g_mid <= 0.0) {
    st.t_hi = t_mid;
    st.g_hi = g_mid;
    st.y_hi = y_mid;
  } else {
    st.t_lo = t_mid;
    st.g_lo = g_mid;
    st.y_lo = y_mid;
  }
  if (st.t_hi - st.t_lo < 1e-10) {
    st.locked = true;
    st.event_time = 0.5 * (st.t_lo + st.t_hi);
  }
}
