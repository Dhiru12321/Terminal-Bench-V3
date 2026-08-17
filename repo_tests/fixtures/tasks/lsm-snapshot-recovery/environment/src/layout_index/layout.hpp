#pragma once

namespace ts {

class LayoutLedger {
 public:
  int generation() const { return gen_; }
  void bump_by(int delta) { gen_ += delta; }
  void set_generation(int g) { gen_ = g; }

 private:
  int gen_{0};
};

}  // namespace ts
