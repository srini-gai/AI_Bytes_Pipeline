"""
One-time script to obtain a YouTube OAuth2 refresh token for the Tamil channel.

Run:
    python get_tamil_token.py

A browser window opens — sign in with the Tamil channel Google account.
The refresh token is printed and saved to .env as YOUTUBE_REFRESH_TOKEN_TA.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

client_id     = os.getenv("YOUTUBE_CLIENT_ID", "")
client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")

if not client_id or not client_secret:
    print("ERROR: YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET must be set in .env")
    sys.exit(1)

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=SCOPES,
)

print("\nOpening browser — sign in with the TAMIL channel Google account.")
print("If the wrong account opens, use an incognito window.\n")

creds = flow.run_local_server(port=0)

refresh_token = creds.refresh_token
print(f"\nTAMIL REFRESH TOKEN: {refresh_token}\n")

# Append to .env if YOUTUBE_REFRESH_TOKEN_TA is not already set
env_path = Path(__file__).parent / ".env"
env_text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

if "YOUTUBE_REFRESH_TOKEN_TA" in env_text:
    print(".env already contains YOUTUBE_REFRESH_TOKEN_TA — update it manually.")
else:
    with env_path.open("a", encoding="utf-8") as f:
        f.write(f"\nYOUTUBE_REFRESH_TOKEN_TA={refresh_token}\n")
    print("Saved to .env as YOUTUBE_REFRESH_TOKEN_TA")
