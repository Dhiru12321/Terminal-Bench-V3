#include "persistence/writer.hpp"

#include <cstring>
#include <fstream>

#include "persistence/bundle_format.hpp"

namespace {

template <class T>
void wraw(std::ofstream& o, const T& v) {
  o.write(reinterpret_cast<const char*>(&v), sizeof(T));
}

}  // namespace

void BundleWriter::audit_line(const std::string& msg) {
  std::ofstream a(audit_path_, std::ios::app);
  if (a) {
    a << msg << '\n';
  }
}

bool BundleWriter::write(const std::string& path, std::uint64_t op_sig, const BundlePayload& p) {
  std::ofstream out(path, std::ios::binary | std::ios::trunc);
  if (!out) {
    return false;
  }
  wraw(out, bundle_magic());
  wraw(out, bundle_layout_version());
  wraw(out, op_sig);
  wraw(out, p.t);
  wraw(out, p.dt);
  for (double v : p.y) {
    wraw(out, v);
  }
  wraw(out, p.accepted);
  wraw(out, p.rejected);
  wraw(out, p.accepted_at_snapshot);
  wraw(out, p.stage_index);
  for (double v : p.k1) {
    wraw(out, v);
  }
  for (double v : p.k2) {
    wraw(out, v);
  }
  wraw(out, p.newton.iter_count);
  wraw(out, p.newton.alpha);
  for (double v : p.newton.k_guess) {
    wraw(out, v);
  }
  wraw(out, p.newton.had_ls_backoff);
  wraw(out, p.err_prev);
  const double integral_wire = 0.0;
  wraw(out, integral_wire);
  std::uint32_t ev_active = p.event.active ? 1u : 0u;
  wraw(out, ev_active);
  wraw(out, p.event.t_lo);
  wraw(out, p.event.t_hi);
  wraw(out, p.event.g_lo);
  wraw(out, p.event.g_hi);
  std::uint32_t ev_locked = p.event.locked ? 1u : 0u;
  wraw(out, ev_locked);
  wraw(out, p.event.event_time);
  for (double v : p.event.y_lo) {
    wraw(out, v);
  }
  for (double v : p.event.y_hi) {
    wraw(out, v);
  }
  wraw(out, p.event.shrink_pass);
  wraw(out, p.after_pi_for_step);
  return static_cast<bool>(out);
}
