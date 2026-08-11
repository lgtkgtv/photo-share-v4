#!/bin/bash
# Generate .env.auth-service and .env.application from their .example templates,
# filling in real random secrets. Idempotent: does nothing if both files already
# exist, so it's safe to call from quickstart.sh on every run.
#
# The one thing that MUST be consistent across both generated files is
# JWT_SECRET_KEY -- the auth service signs tokens with it, the app service
# verifies them with it, and a mismatch means every request looks unauthenticated.
# Database passwords must also match what docker-compose.separated.yml configures
# for the auth-db/app-db containers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

AUTH_ENV=".env.auth-service"
APP_ENV=".env.application"

if [ -f "$AUTH_ENV" ] && [ -f "$APP_ENV" ]; then
    echo "✅ $AUTH_ENV and $APP_ENV already exist -- leaving them as-is."
    echo "   (delete them and re-run this script to regenerate with fresh secrets)"
    exit 0
fi

if [ ! -f "$AUTH_ENV.example" ] || [ ! -f "$APP_ENV.example" ]; then
    echo "❌ Missing $AUTH_ENV.example or $APP_ENV.example -- can't generate env files."
    exit 1
fi

random_secret() {
    # URL-safe, no padding -- safe to drop straight into a .env value.
    openssl rand -base64 48 | tr '+/' '-_' | tr -d '=\n'
}

fernet_key() {
    # A Fernet key is just 32 random bytes, base64-urlsafe encoded (with padding).
    openssl rand -base64 32 | tr '+/' '-_'
}

echo "🔐 Generating environment files with fresh random secrets..."

# NOTE: AUTH_POSTGRES_PASSWORD / APP_POSTGRES_PASSWORD are intentionally left as
# the .example templates' values (auth_secure_password_here / app_secure_password_here)
# -- those exact strings are hardcoded in docker-compose.separated.yml's auth-db/app-db
# container definitions, not read from these files, so randomizing them here would
# just break the service-to-database connection.
JWT_SECRET="$(random_secret)"
TWOFA_KEY="$(fernet_key)"
STORAGE_SECRET="$(random_secret)"

sed \
    -e "s#^JWT_SECRET_KEY=.*#JWT_SECRET_KEY=${JWT_SECRET}#" \
    -e "s#^TWOFA_ENCRYPTION_KEY=.*#TWOFA_ENCRYPTION_KEY=${TWOFA_KEY}#" \
    "$AUTH_ENV.example" > "$AUTH_ENV"

sed \
    -e "s#^JWT_SECRET_KEY=.*#JWT_SECRET_KEY=${JWT_SECRET}#" \
    -e "s#^STORAGE_SECRET_KEY=.*#STORAGE_SECRET_KEY=${STORAGE_SECRET}#" \
    "$APP_ENV.example" > "$APP_ENV"

echo "✅ Wrote $AUTH_ENV and $APP_ENV (gitignored, not committed)"
echo "   Both share the same freshly generated JWT_SECRET_KEY, as required."
