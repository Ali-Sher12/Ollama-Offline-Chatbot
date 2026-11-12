# ═══════════════════════════════════════════════════════════════════════════
# Ollama Desktop Chatbot — Multi-stage Docker Build
# ═══════════════════════════════════════════════════════════════════════════
# Stage 1: dependency builder (keeps final image lean)
FROM python:3.11-slim AS builder

WORKDIR /build

# System build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ═══════════════════════════════════════════════════════════════════════════
# Stage 2: runtime image
FROM python:3.11-slim AS runtime

WORKDIR /app

# ── Runtime OS packages the agent can use from the shell ────────────────
# These are the tools the AI agent can invoke via run_terminal.
# Feel free to add more (e.g. nodejs, npm, rust, java, ruby) as needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core shell utilities
    bash curl wget git \
    # Text / search tools
    ripgrep fd-find jq \
    # Archive tools
    zip unzip tar gzip bzip2 \
    # Build essentials (for pip packages that need to compile)
    build-essential \
    # Python helpers
    python3-pip python3-venv \
    # Node.js (for JS projects)
    nodejs npm \
    # Network tools
    netcat-openbsd dnsutils \
    # Misc
    file tree less \
    && rm -rf /var/lib/apt/lists/* \
    # Alias fd (Debian calls it fdfind)
    && ln -sf /usr/bin/fdfind /usr/local/bin/fd || true

# ── Python packages from builder ────────────────────────────────────────
COPY --from=builder /install /usr/local

# ── Environment ─────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    # Agent runs headless inside Docker; point it at the bundled or host Ollama
    OLLAMA_URL=http://host.docker.internal:11434 \
    # Give the agent a sensible workspace inside the container
    AGENT_WORKSPACE=/workspace \
    # Default to allow_all in Docker (user controls the container)
    AGENT_PERMISSION_MODE=allow_all \
    # Increase default agent command timeout for Docker builds
    AGENT_TIMEOUT_SECONDS=300

# ── Application code ────────────────────────────────────────────────────
COPY . .

# ── Persistent directories ──────────────────────────────────────────────
RUN mkdir -p /app/data /workspace /app/static/uploads

# ── Non-root user for better security ───────────────────────────────────
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app /workspace
USER appuser

# ── Expose & run ────────────────────────────────────────────────────────
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

CMD ["python", "main.py", "--headless"]
