#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "harness/app_config.hpp"
#include "integrator/butcher.hpp"
#include "integrator/cycle_orchestrator.hpp"
#include "persistence/bundle_format.hpp"
#include "persistence/reader.hpp"
#include "persistence/writer.hpp"

namespace {

std::string fmt_vec(const std::array<double, 3>& v) {
  std::ostringstream o;
  o.setf(std::ios::fixed);
  o.precision(17);
  o << "[" << v[0] << "," << v[1] << "," << v[2] << "]";
  return o.str();
}

void append_schedule_json(std::ostringstream& o, const std::string& key, const ScheduleResult& r) {
  o << "\"" << key << "\":{";
  o << "\"ok\":" << (r.ok ? "true" : "false") << ",";
  o << "\"final_time\":" << r.final_time << ",";
  o << "\"final_state\":" << fmt_vec(r.final_y) << ",";
  o << "\"accepted_steps\":" << r.accepted_steps << ",";
  o << "\"rejected_steps\":" << r.rejected_steps << ",";
  o << "\"newton_iterations\":" << r.newton_iterations << ",";
  if (r.had_event) {
    o << "\"event_time\":" << r.event_time;
  } else {
    o << "\"event_time\":null";
  }
  o << "}";
}

bool run_integrity_probes(const AppConfig& base_cfg, const std::string& audit_path,
                          const std::string& bundle_path) {
  std::filesystem::remove(bundle_path);
  BundleWriter w(audit_path);
  BundleReader r(audit_path);
  const std::uint64_t sig_ok = fnv1a64(operator_fingerprint_string(base_cfg));

  BundlePayload p{};
  p.t = base_cfg.t_start;
  p.y = base_cfg.y0;
  p.dt = base_cfg.initial_dt;
  p.accepted = 0;
  p.rejected = 0;
  p.accepted_at_snapshot = 0;
  p.stage_index = 0;
  if (!w.write(bundle_path, sig_ok, p)) {
    return false;
  }

  AppConfig k0_bad = base_cfg;
  k0_bad.model.k0 += 1e-5;
  const std::uint64_t sig_k0 = fnv1a64(operator_fingerprint_string(k0_bad));
  BundlePayload out{};
  std::string reason;
  if (r.try_load(bundle_path, sig_k0, out, reason) || reason != "SIGNATURE_MISMATCH") {
    return false;
  }

  std::filesystem::remove(bundle_path);
  if (!w.write(bundle_path, sig_ok, p)) {
    return false;
  }
  AppConfig damp_bad = base_cfg;
  damp_bad.stability_extra_damping += 0.25;
  const std::uint64_t sig_d = fnv1a64(operator_fingerprint_string(damp_bad));
  if (r.try_load(bundle_path, sig_d, out, reason) || reason != "SIGNATURE_MISMATCH") {
    return false;
  }
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  (void)argc;
  (void)argv;
  const std::string cfg_path = "/app/data/default.toml";
  const std::string work_dir = "/app/work";
  const std::string out_dir = "/app/out";
  const std::string bundle_path = work_dir + "/snapshot.bin";
  const std::string audit_path = out_dir + "/persistence_audit.log";
  const std::string report_path = out_dir + "/restart_report.json";

  std::filesystem::create_directories(work_dir);
  std::filesystem::create_directories(out_dir);
  {
    std::ofstream trunc_audit(audit_path, std::ios::trunc);
  }

  AppConfig cfg{};
  if (!load_app_config(cfg_path, cfg)) {
    std::cerr << "config load failed\n";
    return 2;
  }

  const std::uint64_t op_checksum = fnv1a64(operator_fingerprint_string(cfg));
  bool probe_ok = run_integrity_probes(cfg, audit_path, bundle_path);
  bool probe_op = false;
  bool probe_damp = false;
  if (probe_ok) {
    probe_op = true;
    probe_damp = true;
  }

  const butcher::Tableau tab = butcher::make_table(cfg.butcher_gamma);

  BundleWriter writer(audit_path);
  BundleReader reader(audit_path);

  std::ostringstream sched_json;
  sched_json << "{";
  bool first = true;
  for (ScheduleId sid : {ScheduleId::A, ScheduleId::B, ScheduleId::C}) {
    CycleOrchestrator orch;
    orch.configure(cfg, tab);
    orch.set_schedule(sid);
    ScheduleResult sr = orch.run_with_interrupt(bundle_path, writer, reader);
    if (!first) {
      sched_json << ",";
    }
    first = false;
    append_schedule_json(sched_json, schedule_key(sid), sr);
  }
  sched_json << "}";

  std::ofstream rep(report_path, std::ios::trunc);
  if (!rep) {
    return 4;
  }
  rep << "{";
  rep << "\"operator_signature_checksum\":" << op_checksum << ",";
  rep << "\"integrity_probes\":{";
  rep << "\"stale_operator_bundle_rejected\":" << (probe_op ? "true" : "false") << ",";
  rep << "\"stale_damping_bundle_rejected\":" << (probe_damp ? "true" : "false");
  rep << "},";
  rep << "\"schedules\":" << sched_json.str();
  rep << "}\n";
  return 0;
}
