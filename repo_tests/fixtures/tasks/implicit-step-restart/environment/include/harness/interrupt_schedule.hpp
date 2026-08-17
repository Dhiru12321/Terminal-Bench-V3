#pragma once

#include <cstdint>
#include <string>

enum class ScheduleId { A, B, C };

enum class HookKind { None, AfterStage0, MidNewtonStage1, AfterPiBeforeStageCommit };

struct HookContext {
  std::uint32_t accepted_complete{};
  int stage_index{};
  int newton_iter{};
  int had_ls_backoff{};
};

HookKind interrupt_for(ScheduleId sid, const HookContext& ctx);

std::string schedule_key(ScheduleId s);
