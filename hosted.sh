#!/bin/sh
# Server start (see Dockerfile). Fly mounts the state volume owned by root, so hand it to the lucidity user
# and drop to that user. Then pass the AI key (an environment secret) to Lucidity in a private file it reads
# once and deletes, and start Lucidity without the key in its environment, so the programs the agents
# write and run can't read it.
set -e
if [ "$(id -u)" = 0 ]; then
  chown -R lucidity:lucidity /app/state /app/logs
  exec setpriv --reuid=lucidity --regid=lucidity --init-groups sh /app/hosted.sh
fi
umask 077
f=$(mktemp)
printf '%s' "${OPENAI_API_KEY:-$ANTHROPIC_API_KEY}" > "$f"
exec env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY LUCIDITY_KEY_FILE="$f" HOME=/home/lucidity python app.py
