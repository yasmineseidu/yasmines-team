#!/usr/bin/env python3
"""Simple OAuth redirect server to capture authorization code.

Runs a local server on port 8000 to capture the authorization code
from Google's redirect after user grants permission.

Usage:
    python3 oauth_redirect_server.py

Then visit the authorization URL in your browser:
    https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=http://localhost:8000/api/google/callback&response_type=code&scope=https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/drive.file&access_type=offline
"""

import asyncio
from urllib.parse import urlparse, parse_qs

from aiohttp import web


async def handle_callback(request):
    """Handle OAuth redirect callback from Google."""
    # Get the code from query parameters
    code = request.query.get("code")
    error = request.query.get("error")

    if error:
        error_desc = request.query.get("error_description", "Unknown error")
        html = f"""
        <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: Arial; padding: 20px;">
                <h1>❌ Authorization Failed</h1>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Description:</strong> {error_desc}</p>
                <p>Please try again.</p>
            </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    if code:
        html = f"""
        <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: Arial; padding: 20px;">
                <h1>✅ Authorization Successful!</h1>
                <p>Copy this code:</p>
                <p style="background: #f0f0f0; padding: 10px; border-radius: 5px; font-family: monospace;">
                    <strong>{code}</strong>
                </p>
                <p>Use it with the exchange script:</p>
                <pre style="background: #f0f0f0; padding: 10px; border-radius: 5px;">
export GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}"
export GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET}"
python3 app/backend/scripts/exchange_oauth_code.py {code}
                </pre>
                <p>This server will shut down automatically in 60 seconds.</p>
            </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    html = """
    <html>
        <head><title>Waiting for Authorization</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>🔐 OAuth Redirect Server Running</h1>
            <p>Waiting for authorization code from Google...</p>
            <p><a href="https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=http://localhost:8000/api/google/callback&response_type=code&scope=https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/drive.file&access_type=offline">Click here to authorize</a></p>
            <p>Or visit this URL in your browser:</p>
            <p style="font-size: 12px; word-break: break-all;">
                https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=http://localhost:8000/api/google/callback&response_type=code&scope=https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/drive.file&access_type=offline
            </p>
        </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


async def main():
    """Start the OAuth redirect server."""
    print()
    print("=" * 70)
    print("🔐 GOOGLE OAUTH REDIRECT SERVER")
    print("=" * 70)
    print()
    print("Server running on http://localhost:8000/api/google/callback")
    print()
    print("📍 STEP 1: Click link or paste URL in browser:")
    print()
    print("https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=http://localhost:8000/api/google/callback&response_type=code&scope=https://www.googleapis.com/auth/drive%20https://www.googleapis.com/auth/drive.file&access_type=offline")
    print()
    print("📍 STEP 2: Grant permission when prompted")
    print()
    print("📍 STEP 3: Copy the code from the page that appears")
    print()
    print("📍 STEP 4: Use with exchange script:")
    print("   python3 app/backend/scripts/exchange_oauth_code.py <code>")
    print()
    print("⏳ Server will auto-shutdown after 60 seconds with no requests")
    print("=" * 70)
    print()

    # Create web app
    app = web.Application()
    app.router.add_get("/api/google/callback", handle_callback)

    # Create and start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8000)
    await site.start()

    # Run for 60 seconds then shutdown
    try:
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        await runner.cleanup()
        print()
        print("🛑 Server shutdown")


if __name__ == "__main__":
    asyncio.run(main())
