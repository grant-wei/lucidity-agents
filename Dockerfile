# Lucidity on a server (grantwei.com/lucidity). Runs, worktrees and uploads live under /app/state,
# which fly.toml mounts as a volume so they survive restarts. The API key comes in as a secret.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/* \
 && git config --system user.name "Lucidity" && git config --system user.email "lucidity@localhost" \
 && git config --system --add safe.directory '*' \
 && useradd --create-home lucidity
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=lucidity:lucidity . .
RUN mkdir -p state logs && chown -R lucidity:lucidity state logs
ENV LUCIDITY_HOSTED=1 LUCIDITY_BASE=/lucidity LUCIDITY_PORT=8080 LUCIDITY_NO_BROWSER=1 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["sh", "hosted.sh"]
