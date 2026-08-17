FROM public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    cmake \
    g++ \
    make \
    tmux \
    && rm -rf /var/lib/apt/lists/*

COPY CMakeLists.txt /app/CMakeLists.txt
COPY data /app/data
COPY include /app/include
COPY src /app/src

RUN cmake -S /app -B /app/build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /app/build -j2
