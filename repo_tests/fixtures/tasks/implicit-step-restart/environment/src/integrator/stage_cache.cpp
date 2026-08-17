#include "integrator/stage_cache.hpp"

void StageCache::reset_stage() {
  current_stage = 0;
  k1 = {};
  k2 = {};
}
