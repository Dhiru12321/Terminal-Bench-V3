#include "engine/types.h"

namespace game {

// Lightweight component ids for future expansion; positions live on `World`.
struct EntitySlot {
  eng::PlayerIndex owner = 0;
};

struct ComponentArena {
  EntitySlot slots[eng::kPlayerCount]{};
};

}  // namespace game
