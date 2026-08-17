#include "persistence/reader.hpp"

#include <fstream>

#include "persistence/bundle_format.hpp"

namespace {

template <class T>
bool rraw(std::ifstream& i, T& v) {
  i.read(reinterpret_cast<char*>(&v), sizeof(T));
  return static_cast<bool>(i);
}

}  // namespace

void BundleReader::audit_line(const std::string& msg) {
  std::ofstream a(audit_path_, std::ios::app);
  if (a) {
    a << msg << '\n';
  }
}

bool BundleReader::try_load(const std::string& path, std::uint64_t expected_sig, BundlePayload& out,
                            std::string& reason) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    reason = "NO_FILE";
    return false;
  }
  std::uint32_t mag{};
  std::uint32_t lay{};
  std::uint64_t sig{};
  if (!rraw(in, mag) || !rraw(in, lay) || !rraw(in, sig)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  if (mag != bundle_magic()) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  if (lay != bundle_layout_version()) {
    reason = "VERSION_MISMATCH";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=VERSION_MISMATCH");
    return false;
  }
  if (sig != expected_sig) {
    reason = "SIGNATURE_MISMATCH";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=SIGNATURE_MISMATCH");
    return false;
  }
  if (!rraw(in, out.t) || !rraw(in, out.dt)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  for (double& v : out.y) {
    if (!rraw(in, v)) {
      reason = "CORRUPT_BUNDLE";
      audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
      return false;
    }
  }
  if (!rraw(in, out.accepted) || !rraw(in, out.rejected) || !rraw(in, out.accepted_at_snapshot) ||
      !rraw(in, out.stage_index)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  for (double& v : out.k1) {
    if (!rraw(in, v)) {
      reason = "CORRUPT_BUNDLE";
      audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
      return false;
    }
  }
  for (double& v : out.k2) {
    if (!rraw(in, v)) {
      reason = "CORRUPT_BUNDLE";
      audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
      return false;
    }
  }
  if (!rraw(in, out.newton.iter_count) || !rraw(in, out.newton.alpha)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  for (double& v : out.newton.k_guess) {
    if (!rraw(in, v)) {
      reason = "CORRUPT_BUNDLE";
      audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
      return false;
    }
  }
  if (!rraw(in, out.newton.had_ls_backoff)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  if (!rraw(in, out.err_prev)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  double integral_disk{};
  if (!rraw(in, integral_disk)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  (void)integral_disk;
  out.integral_err = 0.0;
  std::uint32_t ev_active{};
  if (!rraw(in, ev_active) || !rraw(in, out.event.t_lo) || !rraw(in, out.event.t_hi) ||
      !rraw(in, out.event.g_lo) || !rraw(in, out.event.g_hi)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  out.event.active = ev_active != 0;
  std::uint32_t ev_locked{};
  if (!rraw(in, ev_locked) || !rraw(in, out.event.event_time)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  out.event.locked = ev_locked != 0;
  for (double& v : out.event.y_lo) {
    if (!rraw(in, v)) {
      reason = "CORRUPT_BUNDLE";
      audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
      return false;
    }
  }
  for (double& v : out.event.y_hi) {
    if (!rraw(in, v)) {
      reason = "CORRUPT_BUNDLE";
      audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
      return false;
    }
  }
  if (!rraw(in, out.event.shrink_pass)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  if (!rraw(in, out.after_pi_for_step)) {
    reason = "CORRUPT_BUNDLE";
    audit_line("ATTEMPT LOAD " + path + " STATUS=REJECTED REASON=CORRUPT_BUNDLE");
    return false;
  }
  audit_line("ATTEMPT LOAD " + path + " STATUS=ACCEPTED REASON=OK");
  reason = "OK";
  return true;
}
