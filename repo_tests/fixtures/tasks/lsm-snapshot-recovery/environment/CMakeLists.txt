cmake_minimum_required(VERSION 3.18)
project(tile_store CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(nlohmann_json 3.2.0 REQUIRED)

add_library(store STATIC
  src/api/engine.cpp
  src/wal_record/wal.cpp
  src/buffer/buffer.cpp
  src/tile/tile.cpp
  src/layout_index/layout.cpp
  src/level_merge/merge.cpp
  src/cursor_pin/pin.cpp
)

target_include_directories(store PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src")
target_link_libraries(store PUBLIC nlohmann_json::nlohmann_json)

add_executable(trace_driver
  tools/trace_driver.cpp
)
target_include_directories(trace_driver PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
target_link_libraries(trace_driver PRIVATE store nlohmann_json::nlohmann_json)
