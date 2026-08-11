#!/bin/bash
# One-command PhotoShare dev startup: fresh clone -> running local instance.
#
#   ./scripts/quickstart.sh
#
# Generates .env.auth-service / .env.application (with fresh random secrets)
# if they don't already exist, builds and starts the separated-architecture
# docker compose stack, and waits for both services to report healthy.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

COMPOSE_FILE="docker-compose.separated.yml"

echo "🚀 PhotoShare Quickstart"
echo "========================"
echo ""

if ! command -v docker &> /dev/null; then
    echo "❌ docker is not installed. Install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ 'docker compose' (v2 plugin) is not available. Install it first."
    exit 1
fi

echo "📝 Step 1/3: Environment files"
"$SCRIPT_DIR/generate-env-files.sh"
echo ""

echo "🐳 Step 2/3: Building and starting services (this can take a few minutes on first run)"
docker compose -f "$COMPOSE_FILE" up --build -d
echo ""

echo "⏳ Step 3/3: Waiting for services to report healthy..."
AUTH_URL="http://localhost:8001/health"
APP_URL="http://localhost:8000/health"
MAX_WAIT_SECONDS=240
INTERVAL_SECONDS=5
elapsed=0

auth_ready=false
app_ready=false

while [ "$elapsed" -lt "$MAX_WAIT_SECONDS" ]; do
    if [ "$auth_ready" = false ] && curl -sf "$AUTH_URL" > /dev/null 2>&1; then
        auth_ready=true
        echo "   ✅ Auth service healthy ($AUTH_URL)"
    fi
    if [ "$app_ready" = false ] && curl -sf "$APP_URL" > /dev/null 2>&1; then
        app_ready=true
        echo "   ✅ App service healthy ($APP_URL)"
    fi

    if [ "$auth_ready" = true ] && [ "$app_ready" = true ]; then
        break
    fi

    sleep "$INTERVAL_SECONDS"
    elapsed=$((elapsed + INTERVAL_SECONDS))
    echo "   ... still waiting (${elapsed}s/${MAX_WAIT_SECONDS}s)"
done

echo ""

if [ "$auth_ready" = true ] && [ "$app_ready" = true ]; then
    echo "✅ PhotoShare is up:"
    echo "   Auth service: http://localhost:8001"
    echo "   App service:  http://localhost:8000"
    echo ""
    echo "Try it:"
    echo '  curl -X POST http://localhost:8001/api/auth/register \'
    echo '    -H "Content-Type: application/json" \'
    echo "    -d '{\"email\": \"test@example.com\", \"password\": \"TestPass123!\", \"first_name\": \"Test\", \"last_name\": \"User\"}'"
    echo ""
    echo "Logs:   docker compose -f $COMPOSE_FILE logs -f"
    echo "Stop:   docker compose -f $COMPOSE_FILE down"
    echo "Reset:  docker compose -f $COMPOSE_FILE down -v   # also drops database volumes"
else
    echo "❌ Services did not become healthy within ${MAX_WAIT_SECONDS}s."
    echo "   Check logs for details:"
    echo "   docker compose -f $COMPOSE_FILE logs auth-service"
    echo "   docker compose -f $COMPOSE_FILE logs photo-share-app"
    exit 1
fi
