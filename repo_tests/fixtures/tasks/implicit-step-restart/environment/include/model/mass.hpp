#pragma once

#include <array>

void mass_apply(const std::array<double, 3>& v, const std::array<double, 3>& diag,
                std::array<double, 3>& out);

void mass_solve(const std::array<double, 3>& rhs, const std::array<double, 3>& diag,
                std::array<double, 3>& x);
