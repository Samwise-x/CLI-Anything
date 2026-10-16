# Linux amd64 Python image pinned to its immutable manifest.
FROM python:3.12-slim-bookworm@sha256:2ed6491b93cd49272ee6de2b5a38440c3448360322c089fc23e370722d74179d
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates bash curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 agent \
    && useradd --uid 1000 --gid 1000 --home-dir /home/agent --no-create-home agent
USER 1000:1000
WORKDIR /workspace
