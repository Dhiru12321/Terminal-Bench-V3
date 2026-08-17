#!/usr/bin/env bash
# One-shot Docker reachability check for Harbor / verifier_health.
#
# Succeeds whenever `docker` can talk to an engine: native Linux daemon,
# Docker Desktop (macOS/Windows), WSL2 with Desktop integration, or a remote
# daemon via DOCKER_HOST. There is no separate "integration" probe — if
# this passes, Harbor's docker compose builds can use the same context.
set -euo pipefail
if docker version; then
  exit 0
else
  status=$?
echo >&2 ""
echo >&2 "Docker is not reachable (client installed but no daemon on this socket/context)."
echo >&2 "  - Start Docker Desktop or \`sudo service docker start\` on Linux."
echo >&2 "  - Cursor/agent sandboxes often omit /var/run/docker.sock — run Harbor on your host or CI."
echo >&2 "  - WSL2 + Docker Desktop + BuildKit bind failures: use \`bash scripts/harbor-docker-legacy.sh ...\`"
echo >&2 "    (see commands.md → Harbor → Docker / WSL)."
echo >&2 ""
exit "$status"
fi
