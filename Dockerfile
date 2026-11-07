# The public copy of the pit wall (step E1, decision 0018): the read-only app and a data
# snapshot in one image. Built by .github/workflows/release.yml when a release is published.
# To try it on the Mac (needs Docker Desktop): make image, then make image-run.
FROM python:3.12-slim

# uv: the same version as on the Mac (`uv --version`), so uv.lock is read the same way
COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# 1. Libraries first: this layer is reused until pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. The code, the settings and the app's web files
COPY src ./src
RUN uv sync --frozen --no-dev
COPY config ./config
COPY web/app ./web/app
# the race engineer's exam and its recorded answers: shown online instead of live questions
COPY evals/questions.yaml ./evals/questions.yaml
COPY reports/ai ./reports/ai

# 3. The data snapshot (dpec snapshot, unpacked into snapshot/), checked file by file
COPY snapshot/ ./
RUN sha256sum -c SHA256SUMS

# Run as a normal user, not root: the app only reads (so everything must be readable)
RUN useradd --create-home dpec && chmod -R a+rX /app
USER dpec
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/api/health')"
CMD ["/app/.venv/bin/dpec", "serve", "--host", "0.0.0.0", "--port", "7860", "--config", "config/public.yaml"]
