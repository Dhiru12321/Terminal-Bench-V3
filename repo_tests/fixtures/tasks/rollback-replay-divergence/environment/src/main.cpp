#include "harness/runner.h"

#include <iostream>
#include <string>

int main(int argc, char** argv) {
  std::string out_dir = "/app/output";
  std::string pack = "/app/data/seed_scenarios.json";
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--out" && i + 1 < argc) {
      out_dir = argv[++i];
    } else if (a == "--pack" && i + 1 < argc) {
      pack = argv[++i];
    }
  }
  try {
    return harness::run_matrix(pack, out_dir);
  } catch (const std::exception& ex) {
    std::cerr << ex.what() << '\n';
    return 3;
  }
}
