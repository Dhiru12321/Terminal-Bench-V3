# Dockerfile & Image Best Practices

This is the canonical requirements and reference page for Dockerfile and image
quality in Terminus 3 tasks. Two images are in scope: the agent environment
built from `environment/Dockerfile`, and the verifier built from
`tests/Dockerfile`, which runs in its own container the agent cannot reach.

For enforcement, see `scripts/run_static_checks.py` (`--only dockerfile`,
`--only build_context`), `scripts/check_canonical_base_image.py`, and
`ci_checks/check-dockerfile-sanity.sh`. Authoring rules live in
`.cursor/rules/task-creation.mdc` and `review-and-submit.mdc`.

## Two separate requirements (both apply)

Base-image policy has **two independent layers**. Satisfying one does not satisfy
the other:

| Requirement | What it means | How it is checked |
|---|---|---|
| **Digest pinning** | Every `FROM` uses `@sha256:<digest>` (except `scratch`) | CI **fails** missing digests |
| **Canonical base image** | Final runtime `FROM` digest matches the canonical list below | `check_canonical_base_image.py` **fails** without justification; **warns** when justified non-canonical |

A digest-pinned `debian:…@sha256:…` image is compliant when its digest matches
the canonical Debian entry. A digest-pinned `python:3.11-slim-bookworm@sha256:…`
with a **different** digest than the canonical Python row is non-compliant unless
justified.

## 1. Pin Base Images by Digest

Every `FROM` line must use an immutable digest. Never use floating tags such as
`latest`. Tags may be included for readability, but the digest is the source of
truth. CI fails any Dockerfile with a `FROM` line lacking `@sha256`, except
`FROM scratch`. The same rule covers every stage of `tests/Dockerfile` and every
pulled `image:` value in `environment/docker-compose.yaml`.

```dockerfile
# Bad — floating tag, no digest
FROM python:3.13-slim-bookworm

# Good — digest is authoritative (canonical Python digest shown)
FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb
```

Do not pin a CPU architecture. `FROM --platform=…` fails CI; tasks stay portable
across architectures.

Update digests deliberately, in reviewable commits.

## 2. Use Sanctioned Runtime Base Images

Prefer the canonical Terminal-Bench base images below over ad hoc public images
for the **final runtime stage**. Builder stages may use task-appropriate
toolchain images, but the final stage is what agents and verifiers run in and is
checked by CI.

**Why a canonical list:** Tasks across the dataset have been fragmenting onto
many slightly different base images (different tags, different registries,
different patch versions) for no real reason. Reusing a small set of canonical
images dramatically improves cache hit rates, reduces verifier startup time, and
keeps the dataset's runtime surface area manageable.

The list intentionally collapses minor version variants into one canonical entry
per family (e.g., the Go entry covers all Go 1.21–1.26 majors plus
alpine/bullseye/bookworm variants — use the canonical row).

### Canonical base images

Use the exact digest-pinned reference from this list whenever possible. Tags and
registry prefixes (`python:…` vs `public.ecr.aws/docker/library/python:…`) may
differ; the **digest** is what must match.

#### Language runtimes

| Image reference | Family | Covers |
|---|---|---|
| `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb` | Python | All Python 3.10/3.11/3.12/3.13 majors + patch + slim/non-slim |
| `public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383` | Node.js | All Node 18/20/22/24 majors + slim/non-slim |
| `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` | Go | All Go 1.21–1.26 majors + alpine/bullseye/bookworm |
| `public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36` | Rust | All Rust 1.75–1.95 + slim/non-slim + bullseye |
| `public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14` | Java (JDK) | All Java 17/21 jdk-jammy/noble variants |
| `public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c` | C / C++ (GCC) | All GCC 12/13/14/15 variants |
| `public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df` | Ruby | All Ruby 3.2/3.3/3.4 + slim/non-slim |

#### Build tools and SDKs

| Image reference | Family | Covers |
|---|---|---|
| `public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e` | Maven | All Maven + temurin-17/21 variants |

#### Distro bases (for minimal or custom images)

| Image reference | Family | Covers |
|---|---|---|
| `public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d` | Debian | All Debian bookworm/bullseye/12.x slim variants |
| `public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932` | Ubuntu | All Ubuntu 22.04/24.04/jammy variants |

The machine-readable source of truth is `scripts/canonical_base_images.py`.

**Final runtime stage only.** The final `FROM` in `environment/Dockerfile` is
what agents and verifiers run in. Earlier builder stages may use
task-appropriate toolchain images (e.g., a `golang:…` builder copying a binary
into a minimal runtime).

### Using a non-canonical base image

Tasks may use a base image not on this list if there's a genuine reason — for
example, a runtime the canonical list doesn't cover, a hardware-specific image,
or a stack that requires a niche distro. The acceptance gate works as follows:

| Final runtime image | Justification | Result |
|---|---|---|
| Canonical (digest matches table above) | Not required | Passes |
| Non-canonical | Present and credible, as a `Dockerfile` comment | Passes; surfaced to reviewers |
| Non-canonical | Empty / missing / boilerplate | Blocked |

The justification must be written in the `Dockerfile` itself. A task `README.md`
section no longer works: Snorkel generates `README.md` at packaging time from the
`task.toml` explanation fields, so an author-written one never reaches CI — and a
`README.md` at the task root is rejected by the zip validator.

Example Dockerfile justification:

```dockerfile
# Non-canonical base image: needs CUDA 12.4 runtime not covered by canonical images.
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04@sha256:…
```

A reviewer may reject a justification that is vague, boilerplate, or that
describes a case an existing canonical image already covers.

At submission, also select **No** on the canonical-base-image field and include
the same justification. Platform eval checks both.

Local check:

```bash
python3 scripts/check_canonical_base_image.py tasks/<task-name>
python3 scripts/check_canonical_base_image.py tasks/<task-name> --strict
```

## 3. Make Builds Reproducible

Pin all dependencies and avoid nondeterministic build steps.

Pin language dependencies with lockfiles:

| Ecosystem | Acceptable pinning |
|---|---|
| Python | `requirements.txt` with exact versions (`==`), `uv.lock`, or `poetry.lock` |
| Node | `package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock` |
| Rust | `Cargo.lock` |
| Go | `go.mod` and `go.sum` |
| JVM | Pinned Maven/Gradle dependency locks where possible |

Direct `pip install` lines in a Dockerfile must pin exact versions with `==` or
install from a pinned requirements file; `pip`, `setuptools`, and `wheel` are the
only exceptions. Apt is the opposite case — see section 4.

Pin downloaded binaries by version and checksum:

```dockerfile
# Bad
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Good
ARG UV_VERSION=0.6.14
ARG UV_SHA256=…
RUN curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz" -o /tmp/uv.tar.gz \
    && echo "${UV_SHA256}  /tmp/uv.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/uv.tar.gz -C /usr/local/bin --strip-components=1 \
    && rm /tmp/uv.tar.gz
```

Avoid:

- `apt-get upgrade`
- Version-pinned apt packages
- Unpinned `npm install` without a lockfile
- Runtime package downloads in `tests/test.sh` or `solution/solve.sh`
- Nondeterministic `curl | sh` without a pinned version and checksum
- Wall-clock time, random paths, hostnames, or usernames embedded at build time
- Bare `nproc` in `environment/Dockerfile`, `tests/test.sh`, or
  `solution/solve.sh`: inside a container it reports the host CPU count, not the
  task's allocation. Use the configured `cpus` value instead.

When the build clones a repository, check out a specific commit.

## 4. Consolidate apt Usage Correctly

Use one apt transaction per stage, and clean the package lists in the same layer
that creates them:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        git \
        tmux \
    && rm -rf /var/lib/apt/lists/*
```

Rules:

- One `apt-get update && apt-get install -y --no-install-recommends … && rm -rf
  /var/lib/apt/lists/*` transaction per stage.
- Always `--no-install-recommends`.
- Never `apt-get upgrade`.
- **Do not version-pin apt packages.** A line such as `apt-get install -y
  curl=7.88.1-10+deb12u8` fails CI. Distro package versions belong to the base
  image; pin language dependencies instead.
- Keep build tools out of the final runtime stage unless the task requires them.
  Use a multi-stage build when the image compiles or bundles artifacts.

## 5. Bake Every Dependency Into the Image

`[environment].network_mode` is `"public"` by default. Use `"no-network"` only
when the task does not make sense to complete with internet access — for
instance, when network access would let the agent retrieve the answer instead of
doing the work. If in doubt, use `"public"`.

Both values carry the same image requirement: everything the task and the
verifier need is installed at build time, and nothing is fetched at trial time.
`"public"` exists for the task's own work, not as a substitute for a complete
image. Under `"no-network"` a missing dependency is unrecoverable, and the oracle
must pass with the network disabled.

`tmux` and `asciinema` must be installed in the environment image regardless of
`network_mode`; the agent runtime needs both to start a session. Missing them
surfaces as `RuntimeError: Failed to start tmux session` with
`verifier_did_not_run` across every trial. A task with network access may obtain
them some other way during development and appear to work, which is exactly how
this breaks later — install them explicitly.

## 6. Build the Verifier From `tests/Dockerfile`

`tests/Dockerfile` builds a separate verifier image
(`[verifier].environment_mode = "separate"`). The verifier container cannot
reach the agent container and sees only the paths named in the top-level
`artifacts` array of `task.toml`.

The verifier image must:

- Use a digest-pinned `FROM`, the same rule as `environment/Dockerfile`.
- Install every verifier dependency with an exact pin — `pytest` and
  `pytest-json-ctrf` at minimum. `tests/test.sh` runs `python -m pytest` and
  installs nothing at trial time.
- Copy the verifier sources in (`COPY . /tests/`). Separate-mode verifiers
  receive no upload of `tests/`, so the image has to own that directory.
- Create the parent directory of every declared artifact path. Harbor's artifact
  upload fails when the directory is missing, and the failure reads like a broken
  test.

```dockerfile
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

COPY . /tests/

RUN mkdir -p /app
```

Verifier-only tooling belongs here, not in `environment/Dockerfile`. Installing
`playwright`, `ruff`, or a verifier-only Node runtime into the agent image
enlarges the agent's surface for no reason and is flagged by the Dockerfile
check. See `default-template/tests/Dockerfile`.

## 7. Keep the Build Context Small

`environment/` is the build context, and CI measures it:

- At most 100 MiB in total.
- No single file over 50 MiB.
- A `.dockerignore` for any non-trivial environment.
- Prefer `COPY src/ src/` over `COPY . .`.
- Store source as files rather than heredocs, and extract archives at build time
  so individual files stay lazily loadable.

Trim fixtures or generate large data during the build rather than shipping it in
the context. Recommended `.dockerignore`:

```
.git
.gitignore
**/__pycache__/
**/*.pyc
**/.pytest_cache/
**/node_modules/
**/target/
**/dist/
**/build/
**/.venv/
.env
*.log
solution/
tests/
```

## Related Terminus 3 Rules

These Dockerfile policies work together with the rest of the task gates:

- Set `WORKDIR /app` (or another real working directory).
- Do not `COPY` `solution/` or `tests/` into the environment image; Harbor mounts
  them at runtime.
- Do not create or target reserved Harbor paths (`/tests`, `/solution`,
  `/oracle`, `/logs/verifier`, `/logs/artifacts`).
- Do not request privileged mode, `SYS_ADMIN`/`NET_ADMIN`/`SYS_MODULE`
  capabilities, or `docker.sock` access.
- Keep build-artifact directories (`build/`, `target/`, `node_modules/`,
  `__pycache__/`) and pre-computed outputs out of `environment/`.
- Declare `cpus`, `memory_mb`, `storage_mb`, and `build_timeout_sec` under
  `[environment]`. Tasks must not require a GPU.
- Do not author `README.md` or `rubrics.txt`; Snorkel generates both at
  packaging.

See `default-template/environment/Dockerfile` for the minimal Python template.
