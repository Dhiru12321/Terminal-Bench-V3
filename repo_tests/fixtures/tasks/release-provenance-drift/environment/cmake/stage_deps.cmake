# Import graph: artifact roots consumed by staging (paths are relative to /app).
set(STAGE_RUST_RELEASE_SO "${CMAKE_SOURCE_DIR}/../target/release/libplugin_core.so")
set(STAGE_RUST_DEBUG_SO "${CMAKE_SOURCE_DIR}/../target/debug/libplugin_core.so")
set(STAGE_CPP_BUILD_DIR "${CMAKE_BINARY_DIR}")
