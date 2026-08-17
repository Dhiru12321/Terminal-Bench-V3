FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# Every verifier dependency is pinned and baked in; nothing may be installed at trial time.
RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

# Separate-mode verifiers receive no upload of tests/, so the image must own /tests.
# The build context is this tests/ directory.
COPY . /tests/

# Landing directories for every path declared in the top-level `artifacts` array.
# Harbor's artifact upload fails when the parent directory is missing.
RUN mkdir -p /app /app/output /app/bin
