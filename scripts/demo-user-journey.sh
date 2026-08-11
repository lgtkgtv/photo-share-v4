#!/bin/bash
# Full user-journey demo against a REAL Postgres-backed docker-compose stack
# (not SQLite): register -> login -> upload a photo -> create an album ->
# add the photo to the album -> create a share link -> resolve it -> download
# via the signed URL -> comment -> tag -> check analytics.
#
# This exercises the Phase 1 product API (routers/albums.py, shares.py,
# comments.py, tags.py, analytics.py) against real Postgres for the first
# time -- until now it had only been verified against SQLite in unit/e2e
# tests. Run ./scripts/quickstart.sh first if the stack isn't already up.
#
# Any step that fails prints the response body and exits non-zero -- this
# script is meant to surface real breakage, not paper over it.

set -uo pipefail

AUTH_URL="http://localhost:8001"
APP_URL="http://localhost:8000"
EMAIL="journey-$(date +%s)@example.com"
PASSWORD="TestPass123!"

step_num=0
fail() {
    echo ""
    echo "❌ FAILED at step $step_num: $1"
    echo "Response: $2"
    exit 1
}

step() {
    step_num=$((step_num + 1))
    echo ""
    echo "── Step $step_num: $1 ──"
}

require_status() {
    local expected="$1" actual="$2" body="$3" label="$4"
    if [ "$actual" != "$expected" ]; then
        fail "$label (expected HTTP $expected, got $actual)" "$body"
    fi
}

echo "🎬 PhotoShare full user-journey demo (real Postgres via docker-compose.separated.yml)"
echo "   auth: $AUTH_URL   app: $APP_URL"

# Sanity: both services must already be healthy (run ./scripts/quickstart.sh first)
if ! curl -sf "$AUTH_URL/health" > /dev/null || ! curl -sf "$APP_URL/health" > /dev/null; then
    echo "❌ Services aren't up. Run ./scripts/quickstart.sh first."
    exit 1
fi

step "Register user ($EMAIL)"
resp=$(curl -s -w "\n%{http_code}" -X POST "$AUTH_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\", \"first_name\": \"Journey\", \"last_name\": \"Demo\"}")
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 200 "$code" "$body" "register"
echo "✅ Registered"

step "Login"
resp=$(curl -s -w "\n%{http_code}" -X POST "$AUTH_URL/api/auth/login" \
    -F "username=$EMAIL" -F "password=$PASSWORD")
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 200 "$code" "$body" "login"
TOKEN=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
[ -n "$TOKEN" ] || fail "login" "no access_token in response: $body"
echo "✅ Logged in, got a JWT"

step "Upload a photo (POST /api/photos/upload)"
# Minimal valid JPEG
python3 -c "
import struct
data = bytes.fromhex('FFD8FFE000104A46494600010101006000600000FFDB004300080606070605080707') + b'\\x00' * 200 + bytes.fromhex('FFD9')
open('/tmp/journey-test.jpg', 'wb').write(data)
"
resp=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/api/photos/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/journey-test.jpg;type=image/jpeg" \
    -F "title=Journey Test Photo" \
    -F "description=Uploaded by demo-user-journey.sh" \
    -F "is_public=true")
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 200 "$code" "$body" "photo upload"
PHOTO_ID=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
[ -n "$PHOTO_ID" ] || fail "photo upload" "no id in response: $body"
echo "✅ Uploaded photo id=$PHOTO_ID"

step "Create an album (POST /api/albums/)"
resp=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/api/albums/" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"name": "Journey Demo Album", "description": "Created by demo-user-journey.sh", "is_public": true}')
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 201 "$code" "$body" "create album"
ALBUM_ID=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
[ -n "$ALBUM_ID" ] || fail "create album" "no id in response: $body"
echo "✅ Created album id=$ALBUM_ID"

step "Add photo to album (POST /api/albums/$ALBUM_ID/photos)"
resp=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/api/albums/$ALBUM_ID/photos" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"photo_ids\": [$PHOTO_ID]}")
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 201 "$code" "$body" "add photo to album"
echo "✅ Added photo to album"

step "Create a share link (POST /api/photos/$PHOTO_ID/share)"
resp=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/api/photos/$PHOTO_ID/share" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"share_type": "public"}')
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 201 "$code" "$body" "create share"
SHARE_TOKEN=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin)['share_token'])")
[ -n "$SHARE_TOKEN" ] || fail "create share" "no share_token in response: $body"
echo "✅ Created share, token=$SHARE_TOKEN"

step "Resolve the share (GET /api/shares/$SHARE_TOKEN, anonymous)"
resp=$(curl -s -w "\n%{http_code}" "$APP_URL/api/shares/$SHARE_TOKEN")
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 200 "$code" "$body" "resolve share"
DOWNLOAD_URL=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin)['download']['url'])")
[ -n "$DOWNLOAD_URL" ] || fail "resolve share" "no download.url in response: $body"
echo "✅ Resolved share, signed download URL: $DOWNLOAD_URL"

step "Download via the signed URL (anonymous, no auth header)"
http_code=$(curl -s -o /tmp/journey-downloaded.jpg -w "%{http_code}" "$APP_URL$DOWNLOAD_URL")
require_status 200 "$http_code" "(binary response)" "signed URL download"
if ! cmp -s /tmp/journey-test.jpg /tmp/journey-downloaded.jpg; then
    fail "signed URL download" "downloaded bytes don't match the uploaded file"
fi
echo "✅ Downloaded via signed URL, bytes match what was uploaded"

step "Comment on the photo (POST /api/photos/$PHOTO_ID/comments)"
resp=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/api/photos/$PHOTO_ID/comments" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"comment": "Nice shot! -- demo-user-journey.sh"}')
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 201 "$code" "$body" "create comment"
echo "✅ Commented"

step "Tag the photo (POST /api/photos/$PHOTO_ID/tags)"
resp=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/api/photos/$PHOTO_ID/tags" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"tags": ["journey-demo", "postgres-verified"]}')
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 201 "$code" "$body" "add tags"
echo "✅ Tagged"

step "Check photo analytics (GET /api/photos/$PHOTO_ID/analytics)"
resp=$(curl -s -w "\n%{http_code}" "$APP_URL/api/photos/$PHOTO_ID/analytics" \
    -H "Authorization: Bearer $TOKEN")
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 200 "$code" "$body" "photo analytics"
echo "✅ Analytics: $body"

step "Check account analytics summary (GET /api/analytics/summary)"
resp=$(curl -s -w "\n%{http_code}" "$APP_URL/api/analytics/summary" \
    -H "Authorization: Bearer $TOKEN")
body=$(echo "$resp" | head -n -1)
code=$(echo "$resp" | tail -n1)
require_status 200 "$code" "$body" "analytics summary"
echo "✅ Summary: $body"

echo ""
echo "🎉 Full user journey passed end-to-end against real Postgres."
