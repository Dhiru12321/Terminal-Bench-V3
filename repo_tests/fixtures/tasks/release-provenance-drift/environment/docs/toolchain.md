# Toolchain

Rust uses the workspace under `/app`. Native helpers build with CMake from `cpp-bridge/`. The loader is built with the host `gcc` invoking `load.c` and linked with `-ldl`.
