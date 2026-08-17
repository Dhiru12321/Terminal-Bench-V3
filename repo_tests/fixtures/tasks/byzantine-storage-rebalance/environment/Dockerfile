# Non-canonical base image: this fixture exercises a Go 1.22 toolchain whose module
# resolution differs from the canonical Go 1.24 image, which is the behaviour the
# replay traces were recorded against.
FROM golang:1.22-bookworm@sha256:1f298b0c9fecdf504389a0329236f948cc04a566a2bb32337207cbaaa2f8177c

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    python3 \
    tmux \
    && rm -rf /var/lib/apt/lists/*

COPY src/. /app/
COPY data/fixtures /app/fixtures
COPY data/config /app/config

RUN go mod download \
    && go build -o /app/storesim ./cmd/storesim \
    && rm -rf /root/.cache/go-build

# Keep the toolchain on PATH for agent rebuilds and pytest subprocesses.
ENV PATH="/usr/local/go/bin:/app:${PATH}"
