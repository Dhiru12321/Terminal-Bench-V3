#include "integrator/cycle_orchestrator.hpp"

#include <cmath>
#include <filesystem>
#include <sstream>

#include "harness/interrupt_schedule.hpp"
#include "nonlinear/embedded_driver.hpp"
#include "persistence/bundle_format.hpp"

namespace {

struct HookEnv {
  const CycleOrchestrator* orch{};
  std::uint32_t accepted_at_step_start{};
  int stage{};
};

bool newton_hook_fn(int newton_iter, const NewtonPersist& p, void* ctx) {
  auto* e = static_cast<HookEnv*>(ctx);
  if (!e->orch->schedule_hooks()) {
    return false;
  }
  HookContext hx{};
  hx.accepted_complete = e->accepted_at_step_start;
  hx.stage_index = e->stage;
  hx.newton_iter = newton_iter;
  hx.had_ls_backoff = p.had_ls_backoff;
  return interrupt_for(e->orch->schedule(), hx) != HookKind::None;
}

double vec_norm_scaled(const std::array<double, 3>& a, const std::array<double, 3>& b, double atol,
                       double rtol) {
  double s = 0.0;
  for (int i = 0; i < 3; ++i) {
    const double sc = atol + rtol * std::max(std::fabs(a[i]), std::fabs(b[i]));
    const double d = (a[i] - b[i]) / std::max(sc, 1e-30);
    s += d * d;
  }
  return std::sqrt(s);
}

}  // namespace

void CycleOrchestrator::configure(const AppConfig& cfg, const butcher::Tableau& tab) {
  cfg_ = cfg;
  tab_ = tab;
}

void CycleOrchestrator::fill_bundle(BundlePayload& snap, double t_anchor,
                                    const std::array<double, 3>& y_anchor, double h_work, int acc, int rej,
                                    int stage_idx, const std::array<double, 3>& k1,
                                    const std::array<double, 3>& k2, const NewtonPersist& np,
                                    const ErrorController& ec, const EventState& evst) {
  snap.t = t_anchor;
  snap.y = y_anchor;
  snap.dt = h_work;
  snap.accepted = static_cast<std::uint32_t>(acc);
  snap.rejected = static_cast<std::uint32_t>(rej);
  snap.accepted_at_snapshot = static_cast<std::uint32_t>(acc);
  snap.stage_index = static_cast<std::uint32_t>(stage_idx);
  snap.k1 = k1;
  snap.k2 = k2;
  snap.newton = np;
  snap.err_prev = ec.err_prev;
  snap.integral_err = ec.integral_err;
  snap.event = evst;
}

void CycleOrchestrator::emit_step_line(double t, const std::array<double, 3>& y, bool accepted) {
  if (!golden_.on || golden_.out == nullptr) {
    return;
  }
  std::ostringstream o;
  o.setf(std::ios::fixed);
  o.precision(17);
  o << "{\"kind\":\"step\",\"t\":" << t << ",\"y\":[";
  o << y[0] << "," << y[1] << "," << y[2] << "],\"accepted\":";
  o << (accepted ? "true" : "false") << "}\n";
  *golden_.out += o.str();
}

ScheduleResult CycleOrchestrator::run_uninterrupted() {
  ScheduleResult out{};
  hooks_enabled_ = false;
  double t = cfg_.t_start;
  std::array<double, 3> y = cfg_.y0;
  double dt = cfg_.initial_dt;
  int acc = 0;
  int rej = 0;
  ErrorController ec{};
  ec.safety = cfg_.safety;
  ec.facmin = cfg_.facmin;
  ec.facmax = cfg_.facmax;
  ec.alpha_pi = cfg_.alpha_pi;
  ec.beta_pi = cfg_.beta_pi;
  EmbeddedDriver drv{};
  drv.set_mass_diag(cfg_.mass_diag);
  drv.set_rhs_params(cfg_.model);
  drv.set_table(tab_);
  drv.reset_counts();
  EventLocalization evloc{};
  evloc.configure(cfg_.event_component, cfg_.event_target);
  EventState evst{};
  NewtonConfig ncfg{cfg_.newton_max, cfg_.newton_tol};
  double g_prev = evloc.g_value(t, y);
  const int kMaxSteps = 200000;

  for (int guard = 0; guard < kMaxSteps && t < cfg_.t_end - 1e-15; ++guard) {
    if (evst.active && !evst.locked) {
      const double tm = 0.5 * (evst.t_lo + evst.t_hi);
      std::array<double, 3> ym{};
      const double w = (tm - evst.t_lo) / std::max(evst.t_hi - evst.t_lo, 1e-30);
      for (int i = 0; i < 3; ++i) {
        ym[i] = (1.0 - w) * evst.y_lo[i] + w * evst.y_hi[i];
      }
      evloc.shrink(tm, ym, evst);
      if (evst.locked) {
        out.had_event = true;
        out.event_time = evst.event_time;
      }
      continue;
    }
    const std::array<double, 3> y0 = y;
    const double t0 = t;
    const double h = dt;
    bool accepted = false;
    std::array<double, 3> k1{};
    std::array<double, 3> k2{};
    for (int inner = 0; inner < 80; ++inner) {
      NewtonPersist p1{};
      int it1 = 0;
      if (!drv.solve_stage(t0, h, 0, y0, {0, 0, 0}, tab_.a11, k1, ncfg, p1, it1)) {
        rej += 1;
        dt *= 0.5;
        continue;
      }
      NewtonPersist p2{};
      std::array<double, 3> acck{};
      for (int i = 0; i < 3; ++i) {
        acck[i] = tab_.a21 * k1[i];
      }
      int it2 = 0;
      if (!drv.solve_stage(t0, h, 1, y0, acck, tab_.a22, k2, ncfg, p2, it2)) {
        rej += 1;
        dt *= 0.5;
        continue;
      }
      std::array<double, 3> y_end{};
      std::array<double, 3> y_hat{};
      for (int i = 0; i < 3; ++i) {
        y_end[i] = y0[i] + h * (tab_.b1 * k1[i] + tab_.b2 * k2[i]);
        y_hat[i] = y0[i] + h * (tab_.bhat1 * k1[i] + tab_.bhat2 * k2[i]);
      }
      const double err = vec_norm_scaled(y_end, y_hat, cfg_.atol, cfg_.rtol);
      if (err <= 1.0) {
        t = t0 + h;
        y = y_end;
        acc += 1;
        accepted = true;
        emit_step_line(t, y, true);
        const double g_new = evloc.g_value(t, y);
        if (!evst.locked && g_prev * g_new < 0.0) {
          evloc.begin_bracket(t0, y0, t, y, evst);
        }
        g_prev = g_new;
        const double fac = ec.suggest_scale(err, 1.0);
        ec.pi_update(err, 1.0);
        dt = std::min(std::max(h * fac, 1e-14), cfg_.t_end - t);
        break;
      }
      rej += 1;
      dt = std::max(h * ec.suggest_scale(err, 1.0), 1e-14);
    }
    if (!accepted) {
      out.ok = false;
      hooks_enabled_ = true;
      return out;
    }
  }
  out.ok = true;
  out.final_time = t;
  out.final_y = y;
  out.accepted_steps = acc;
  out.rejected_steps = rej;
  out.newton_iterations = drv.total_iters();
  if (evst.locked) {
    out.had_event = true;
    out.event_time = evst.event_time;
  }
  hooks_enabled_ = true;
  return out;
}

ScheduleResult CycleOrchestrator::run_with_interrupt(const std::string& bundle_path, BundleWriter& writer,
                                                     BundleReader& reader) {
  ScheduleResult combined{};
  combined.ok = false;
  const std::uint64_t op_sig = fnv1a64(operator_fingerprint_string(cfg_));
  hooks_enabled_ = true;

  auto run_phase = [&](bool resume) -> bool {
    hooks_enabled_ = !resume;
    double t = cfg_.t_start;
    std::array<double, 3> y = cfg_.y0;
    double dt = cfg_.initial_dt;
    int acc = 0;
    int rej = 0;
    ErrorController ec{};
    ec.safety = cfg_.safety;
    ec.facmin = cfg_.facmin;
    ec.facmax = cfg_.facmax;
    ec.alpha_pi = cfg_.alpha_pi;
    ec.beta_pi = cfg_.beta_pi;
    EmbeddedDriver drv{};
    drv.set_mass_diag(cfg_.mass_diag);
    drv.set_rhs_params(cfg_.model);
    drv.set_table(tab_);
    drv.reset_counts();
    EventLocalization evloc{};
    evloc.configure(cfg_.event_component, cfg_.event_target);
    EventState evst{};
    NewtonConfig ncfg{cfg_.newton_max, cfg_.newton_tol};
    double g_prev = evloc.g_value(t, y);

    std::array<double, 3> y_anchor = y;
    double t_anchor = t;
    double h_work = dt;
    std::array<double, 3> k1{};
    std::array<double, 3> k2{};
    int stage_idx = 0;
    NewtonPersist np{};
    bool mid_step = false;

    if (resume) {
      BundlePayload load{};
      std::string rsn;
      if (!reader.try_load(bundle_path, op_sig, load, rsn)) {
        return false;
      }
      if (schedule_ == ScheduleId::C) {
        load.stage_index = 1;
        load.newton.alpha = 1.0;
      }
      t = load.t;
      y = load.y;
      dt = load.dt;
      acc = static_cast<int>(load.accepted);
      rej = static_cast<int>(load.rejected);
      ec.err_prev = load.err_prev;
      ec.integral_err = load.integral_err;
      evst = load.event;
      k1 = load.k1;
      k2 = load.k2;
      stage_idx = static_cast<int>(load.stage_index);
      np = load.newton;
      y_anchor = load.y;
      t_anchor = load.t;
      h_work = load.dt;
      mid_step = (stage_idx < 2);
      g_prev = evloc.g_value(t, y);
    }

    auto save_snap = [&](int stg) {
      BundlePayload snap{};
      fill_bundle(snap, t_anchor, y_anchor, h_work, acc, rej, stg, k1, k2, np, ec, evst);
      writer.write(bundle_path, op_sig, snap);
      combined.newton_iterations += drv.total_iters();
    };

    const int kMaxSteps = 200000;
    for (int guard = 0; guard < kMaxSteps; ++guard) {
      if (t >= cfg_.t_end - 1e-15 && (!evst.active || evst.locked)) {
        break;
      }
      if (evst.active && !evst.locked) {
        const double tm = 0.5 * (evst.t_lo + evst.t_hi);
        std::array<double, 3> ym{};
        const double w = (tm - evst.t_lo) / std::max(evst.t_hi - evst.t_lo, 1e-30);
        for (int i = 0; i < 3; ++i) {
          ym[i] = (1.0 - w) * evst.y_lo[i] + w * evst.y_hi[i];
        }
        evloc.shrink(tm, ym, evst);
        if (evst.locked) {
          combined.had_event = true;
          combined.event_time = evst.event_time;
        }
        continue;
      }

      if (!mid_step) {
        y_anchor = y;
        t_anchor = t;
        h_work = dt;
        stage_idx = 0;
        k1 = {};
        k2 = {};
        np = NewtonPersist{};
      }

      bool step_accepted = false;
      for (int inner = 0; inner < 120; ++inner) {
        const std::array<double, 3> y0 = y_anchor;
        const double t0 = t_anchor;
        const double h = h_work;

        if (stage_idx == 0) {
          HookEnv he{this, static_cast<std::uint32_t>(acc), 0};
          bool hooked = false;
          int it1 = 0;
          EmbeddedDriver::NewtonHook hk =
              schedule_hooks() ? newton_hook_fn : static_cast<EmbeddedDriver::NewtonHook>(nullptr);
          if (!drv.solve_stage(t0, h, 0, y0, {0, 0, 0}, tab_.a11, k1, ncfg, np, it1, hk, &he,
                               &hooked)) {
            if (hooked && !resume) {
              mid_step = true;
              save_snap(0);
              return true;
            }
            if (hooked) {
              return false;
            }
            rej += 1;
            h_work *= 0.5;
            mid_step = false;
            break;
          }
          stage_idx = 1;
          np = NewtonPersist{};
          HookContext ha{};
          ha.accepted_complete = static_cast<std::uint32_t>(acc);
          ha.stage_index = 1;
          ha.newton_iter = 0;
          if (schedule_hooks() && !resume && interrupt_for(schedule_, ha) != HookKind::None) {
            mid_step = true;
            save_snap(1);
            return true;
          }
        }

        if (stage_idx == 1) {
          HookEnv he{this, static_cast<std::uint32_t>(acc), 1};
          bool hooked = false;
          std::array<double, 3> acck{};
          for (int i = 0; i < 3; ++i) {
            acck[i] = tab_.a21 * k1[i];
          }
          int it2 = 0;
          EmbeddedDriver::NewtonHook hk =
              schedule_hooks() ? newton_hook_fn : static_cast<EmbeddedDriver::NewtonHook>(nullptr);
          if (!drv.solve_stage(t0, h, 1, y0, acck, tab_.a22, k2, ncfg, np, it2, hk, &he, &hooked)) {
            if (hooked && !resume) {
              mid_step = true;
              save_snap(1);
              return true;
            }
            if (hooked) {
              return false;
            }
            rej += 1;
            h_work *= 0.5;
            stage_idx = 0;
            mid_step = false;
            break;
          }

          std::array<double, 3> y_end{};
          std::array<double, 3> y_hat{};
          for (int i = 0; i < 3; ++i) {
            y_end[i] = y0[i] + h * (tab_.b1 * k1[i] + tab_.b2 * k2[i]);
            y_hat[i] = y0[i] + h * (tab_.bhat1 * k1[i] + tab_.bhat2 * k2[i]);
          }
          const double err = vec_norm_scaled(y_end, y_hat, cfg_.atol, cfg_.rtol);
          if (err <= 1.0) {
            t = t0 + h;
            y = y_end;
            acc += 1;
            step_accepted = true;
            mid_step = false;
            const double g_new = evloc.g_value(t, y);
            if (!evst.locked && g_prev * g_new < 0.0) {
              evloc.begin_bracket(t0, y0, t, y, evst);
            }
            g_prev = g_new;
            const double fac = ec.suggest_scale(err, 1.0);
            ec.pi_update(err, 1.0);
            dt = std::min(std::max(h * fac, 1e-14), cfg_.t_end - t);
            break;
          }
          rej += 1;
          h_work = std::max(h_work * ec.suggest_scale(err, 1.0), 1e-14);
          stage_idx = 0;
          mid_step = false;
        }

        if (step_accepted) {
          break;
        }
      }
    }

    if (resume) {
      combined.final_time = t;
      combined.final_y = y;
      combined.accepted_steps = acc;
      combined.rejected_steps = rej;
      combined.newton_iterations += drv.total_iters();
      combined.ok = true;
      if (evst.locked) {
        combined.had_event = true;
        combined.event_time = evst.event_time;
      }
      return true;
    }
    return false;
  };

  std::error_code ec_rem;
  std::filesystem::remove(bundle_path, ec_rem);
  if (!run_phase(false)) {
    combined.ok = false;
    return combined;
  }
  if (!run_phase(true)) {
    combined.ok = false;
    return combined;
  }
  return combined;
}
