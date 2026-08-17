#include "harness/app_config.hpp"

#include <cctype>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string trim(std::string s) {
  while (!s.empty() && std::isspace(static_cast<unsigned char>(s.front()))) {
    s.erase(s.begin());
  }
  while (!s.empty() && std::isspace(static_cast<unsigned char>(s.back()))) {
    s.pop_back();
  }
  return s;
}

bool parse_double(const std::string& v, double& out) {
  std::istringstream iss(v);
  iss >> out;
  return static_cast<bool>(iss);
}

bool parse_int(const std::string& v, int& out) {
  std::istringstream iss(v);
  iss >> out;
  return static_cast<bool>(iss);
}

bool parse_array3(const std::string& v, std::array<double, 3>& out) {
  std::string s = trim(v);
  if (!s.empty() && s.front() == '[') {
    s = s.substr(1);
  }
  if (!s.empty() && s.back() == ']') {
    s.pop_back();
  }
  std::vector<double> vals;
  std::istringstream iss(s);
  std::string piece;
  while (std::getline(iss, piece, ',')) {
    piece = trim(piece);
    if (piece.empty()) {
      continue;
    }
    double x{};
    if (!parse_double(piece, x)) {
      return false;
    }
    vals.push_back(x);
  }
  if (vals.size() != 3) {
    return false;
  }
  out = {vals[0], vals[1], vals[2]};
  return true;
}

}  // namespace

std::string operator_fingerprint_string(const AppConfig& cfg) {
  std::ostringstream os;
  os.setf(std::ios::fixed);
  os.precision(17);
  os << "M:" << cfg.mass_diag[0] << "," << cfg.mass_diag[1] << "," << cfg.mass_diag[2];
  os << "|k0:" << cfg.model.k0 << "|k1:" << cfg.model.k1 << "|k2:" << cfg.model.k2;
  os << "|gamma:" << cfg.butcher_gamma << "|damp:" << cfg.stability_extra_damping;
  return os.str();
}

bool load_app_config(const std::string& path, AppConfig& cfg) {
  std::ifstream in(path);
  if (!in) {
    return false;
  }
  std::string line;
  std::string section;
  while (std::getline(in, line)) {
    line = trim(line);
    if (line.empty() || line[0] == '#') {
      continue;
    }
    if (line.front() == '[' && line.back() == ']') {
      section = line.substr(1, line.size() - 2);
      continue;
    }
    const auto eq = line.find('=');
    if (eq == std::string::npos) {
      continue;
    }
    std::string key = trim(line.substr(0, eq));
    std::string val = trim(line.substr(eq + 1));
    auto set_d = [&](double& slot) { parse_double(val, slot); };
    auto set_i = [&](int& slot) { parse_int(val, slot); };
    if (section == "tolerances") {
      if (key == "rtol") {
        set_d(cfg.rtol);
      } else if (key == "atol") {
        set_d(cfg.atol);
      } else if (key == "safety") {
        set_d(cfg.safety);
      } else if (key == "facmin") {
        set_d(cfg.facmin);
      } else if (key == "facmax") {
        set_d(cfg.facmax);
      } else if (key == "alpha_pi") {
        set_d(cfg.alpha_pi);
      } else if (key == "beta_pi") {
        set_d(cfg.beta_pi);
      }
    } else if (section == "newton") {
      if (key == "max_iter") {
        set_i(cfg.newton_max);
      } else if (key == "tol") {
        set_d(cfg.newton_tol);
      }
    } else if (section == "integration") {
      if (key == "t_start") {
        set_d(cfg.t_start);
      } else if (key == "t_end") {
        set_d(cfg.t_end);
      } else if (key == "initial_dt") {
        set_d(cfg.initial_dt);
      } else if (key == "y0") {
        parse_array3(val, cfg.y0);
      }
    } else if (section == "model") {
      if (key == "k0") {
        set_d(cfg.model.k0);
      } else if (key == "k1") {
        set_d(cfg.model.k1);
      } else if (key == "k2") {
        set_d(cfg.model.k2);
      }
    } else if (section == "mass") {
      if (key == "diagonal") {
        parse_array3(val, cfg.mass_diag);
      }
    } else if (section == "discretization") {
      if (key == "stability_extra_damping") {
        set_d(cfg.stability_extra_damping);
      }
    } else if (section == "butcher") {
      if (key == "gamma") {
        set_d(cfg.butcher_gamma);
      }
    } else if (section == "event") {
      if (key == "target_level") {
        set_d(cfg.event_target);
      } else if (key == "component") {
        set_i(cfg.event_component);
      }
    }
  }
  cfg.data_path = path;
  return true;
}
