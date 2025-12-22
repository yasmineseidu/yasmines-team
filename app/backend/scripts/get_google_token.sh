#!/bin/bash
# Get Google OAuth2 access token using device flow
# This allows testing without a web browser

set -e

# Load environment
source "$(dirname "$0")/../../../.env" 2>/dev/null || true

if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "ERROR: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env"
    exit 1
fi

echo "🔐 Getting Google OAuth2 Access Token"
echo "======================================="
echo ""
echo "Method: Device Flow (no browser required)"
echo "Client ID: ${GOOGLE_CLIENT_ID:0:30}..."
echo ""

# Step 1: Request device code
echo "📱 Step 1: Requesting device code..."
DEVICE_RESPONSE=$(curl -s -X POST \
  "https://oauth2.googleapis.com/device/code" \
  -d "client_id=$GOOGLE_CLIENT_ID" \
  -d "scope=https://www.googleapis.com/auth/documents%20https://www.googleapis.com/auth/drive.file")

echo "$DEVICE_RESPONSE" | head -1

DEVICE_CODE=$(echo "$DEVICE_RESPONSE" | grep -o '"device_code":"[^"]*' | cut -d'"' -f4)
USER_CODE=$(echo "$DEVICE_RESPONSE" | grep -o '"user_code":"[^"]*' | cut -d'"' -f4)
VERIFICATION_URL=$(echo "$DEVICE_RESPONSE" | grep -o '"verification_url":"[^"]*' | cut -d'"' -f4)

if [ -z "$DEVICE_CODE" ]; then
    echo "❌ Failed to get device code"
    echo "Response: $DEVICE_RESPONSE"
    exit 1
fi

echo ""
echo "✅ Got device code"
echo ""
echo "🔗 Visit this URL to authorize:"
echo "   $VERIFICATION_URL"
echo ""
echo "📝 Enter this code when prompted:"
echo "   $USER_CODE"
echo ""
echo "⏳ Waiting for authorization (press Ctrl+C to cancel)..."
echo ""

# Step 2: Poll for token
MAX_ATTEMPTS=120  # 2 minutes
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))

    TOKEN_RESPONSE=$(curl -s -X POST \
      "https://oauth2.googleapis.com/token" \
      -d "client_id=$GOOGLE_CLIENT_ID" \
      -d "client_secret=$GOOGLE_CLIENT_SECRET" \
      -d "device_code=$DEVICE_CODE" \
      -d "grant_type=urn:ietf:params:oauth:grant-type:device_code")

    # Check if we got a token
    if echo "$TOKEN_RESPONSE" | grep -q '"access_token"'; then
        ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        EXPIRES_IN=$(echo "$TOKEN_RESPONSE" | grep -o '"expires_in":[0-9]*' | cut -d':' -f2)
        REFRESH_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)

        echo ""
        echo "✅ Authorization successful!"
        echo ""
        echo "🎉 OAuth2 Token Details:"
        echo "========================="
        echo "Access Token: ${ACCESS_TOKEN:0:50}..."
        echo "Expires In: $EXPIRES_IN seconds"
        if [ -n "$REFRESH_TOKEN" ]; then
            echo "Refresh Token: ${REFRESH_TOKEN:0:50}..."
        fi
        echo ""
        echo "📋 Add to .env:"
        echo "GOOGLE_ACCESS_TOKEN=$ACCESS_TOKEN"
        if [ -n "$REFRESH_TOKEN" ]; then
            echo "GOOGLE_REFRESH_TOKEN=$REFRESH_TOKEN"
        fi
        echo ""
        echo "Or run:"
        echo "export GOOGLE_ACCESS_TOKEN='$ACCESS_TOKEN'"

        exit 0
    fi

    # Check for error
    if echo "$TOKEN_RESPONSE" | grep -q '"error"'; then
        ERROR=$(echo "$TOKEN_RESPONSE" | grep -o '"error":"[^"]*' | cut -d'"' -f4)
        if [ "$ERROR" != "authorization_pending" ]; then
            echo "❌ Error: $ERROR"
            exit 1
        fi
    fi

    # Wait before next attempt
    if [ $((ATTEMPT % 10)) -eq 0 ]; then
        echo "⏳ Still waiting... ($ATTEMPT/${MAX_ATTEMPTS})"
    fi

    sleep 1
done

echo "❌ Authorization timeout - user did not authorize within 2 minutes"
exit 1
