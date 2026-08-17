cmake_minimum_required(VERSION 3.25)
project(cpp_bridge LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)

add_library(cpp_bridge SHARED src/bridge.cpp)
set_target_properties(cpp_bridge PROPERTIES OUTPUT_NAME "cpp_bridge")

add_library(legacy SHARED src/legacy.cpp)
set_target_properties(legacy PROPERTIES OUTPUT_NAME "legacy")
