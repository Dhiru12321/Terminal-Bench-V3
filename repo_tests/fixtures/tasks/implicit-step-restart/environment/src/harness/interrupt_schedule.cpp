#include "harness/interrupt_schedule.hpp"

HookKind interrupt_for(ScheduleId sid, const HookContext& ctx) {
  switch (sid) {
    case ScheduleId::A:
      if (ctx.accepted_complete == 1u && ctx.stage_index == 1 && ctx.newton_iter == 0) {
        return HookKind::AfterStage0;
      }
      break;
    case ScheduleId::B:
      if (ctx.accepted_complete == 2u && ctx.stage_index == 1 && ctx.newton_iter == 1) {
        return HookKind::MidNewtonStage1;
      }
      break;
    case ScheduleId::C:
      if (ctx.accepted_complete == 1u && ctx.stage_index == 0 && ctx.newton_iter == 1) {
        return HookKind::AfterPiBeforeStageCommit;
      }
      break;
  }
  return HookKind::None;
}

std::string schedule_key(ScheduleId s) {
  switch (s) {
    case ScheduleId::A:
      return "A";
    case ScheduleId::B:
      return "B";
    case ScheduleId::C:
      return "C";
  }
  return "?";
}
