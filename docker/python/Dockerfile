# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

FROM runtime AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
# WhisperX pulls a multi-gigabyte CUDA stack; only the processing image turns it on.
ARG WITH_ASR=0
WORKDIR /src
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/
COPY apps/cli/pyproject.toml apps/cli/
COPY apps/api/pyproject.toml apps/api/
RUN extras=$([ "$WITH_ASR" = 1 ] && echo --all-extras); \
    uv sync --frozen --no-dev --all-packages --no-install-workspace $extras
COPY packages/core/src packages/core/src
COPY apps/cli/src apps/cli/src
COPY apps/api/src apps/api/src
RUN extras=$([ "$WITH_ASR" = 1 ] && echo --all-extras); \
    uv sync --frozen --no-dev --all-packages --no-editable $extras

FROM runtime AS api
COPY --from=build /opt/venv /opt/venv
EXPOSE 8000
CMD ["uvicorn", "wordcut_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS cli
COPY --from=build /opt/venv /opt/venv
ENTRYPOINT ["wordcut"]
