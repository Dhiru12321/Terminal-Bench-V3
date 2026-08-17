cmake_minimum_required(VERSION 3.20)
project(dem_runner LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(dem_runner
  src/harness/main.cpp
  src/harness/app_config.cpp
  src/harness/interrupt_schedule.cpp
  src/model/rhs.cpp
  src/model/mass.cpp
  src/integrator/butcher.cpp
  src/integrator/cycle_orchestrator.cpp
  src/integrator/stage_cache.cpp
  src/control/error_controller.cpp
  src/nonlinear/embedded_driver.cpp
  src/events/localization.cpp
  src/persistence/bundle_format.cpp
  src/persistence/writer.cpp
  src/persistence/reader.cpp
)

target_include_directories(dem_runner PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/include")

target_compile_options(dem_runner PRIVATE -Wall -Wextra -Wpedantic)
