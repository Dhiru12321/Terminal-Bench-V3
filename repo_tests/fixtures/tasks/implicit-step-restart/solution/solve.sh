#!/usr/bin/env bash
set -euo pipefail

cd /app

sed -i ':a;N;$!ba;s/const double integral_wire = 0\.0;\n  wraw(out, integral_wire);/  wraw(out, p.integral_err);/' src/persistence/writer.cpp
sed -i 's/out\.integral_err = 0\.0;/out.integral_err = integral_disk;/' src/persistence/reader.cpp
sed -i '/if (schedule_ == ScheduleId::C)/,+3d' src/integrator/cycle_orchestrator.cpp

cmake --build /app/build -j2
/app/build/dem_runner
