"""
Phase 7 - Publisher Agent
Uploads ep{NN}_final_{LANG}.mp4 to the correct YouTube channel with a scheduled
publish time. Runs once per language per episode.

Credential priority (highest to lowest):
  1. YOUTUBE_REFRESH_TOKEN in .env  — headless VPS path (no browser needed)
  2. credentials/token_{lang}.pickle — stored token from a prior browser flow
  3. credentials/client_secrets.json — triggers browser OAuth (dev only)
"""
import json
import logging
import os
import pickle
import time
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY_ID = "28"          # Science & Technology
CHUNK_SIZE = 4 * 1024 * 1024   # 4 MB resumable upload chunks

CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"


def _episode_dir(episode: int, week: int) -> Path:
    base = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))
    return base / f"week_{week:02d}" / f"ep{episode:02d}"


def _token_path(lang: str) -> Path:
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    return CREDENTIALS_DIR / f"token_{lang}.pickle"


def _client_secrets_path() -> Path:
    path = CREDENTIALS_DIR / "client_secrets.json"
    if not path.exists():
        raise RuntimeError(
            f"No OAuth client secrets found at {path}. "
            "Download from Google Cloud Console (APIs & Services -> Credentials) "
            "and save as credentials/client_secrets.json"
        )
    return path


def _build_credentials_from_env() -> Credentials | None:
    """
    Build OAuth2 credentials from .env refresh token.
    Returns None if YOUTUBE_REFRESH_TOKEN is not set/configured.
    """
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
    client_id     = os.getenv("YOUTUBE_CLIENT_ID", "")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")

    if not refresh_token or "your-" in refresh_token:
        return None
    if not client_id or not client_secret:
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    logger.info("YouTube credentials loaded from .env refresh token")
    return creds


def _build_credentials_from_pickle(lang: str) -> Credentials | None:
    """Load + refresh stored pickle credentials. Returns None if missing/invalid."""
    token_path = _token_path(lang)
    if not token_path.exists():
        return None

    with open(token_path, "rb") as f:
        creds = pickle.load(f)

    if creds and creds.valid:
        logger.info(f"YouTube credentials loaded from {token_path}")
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)
        logger.info(f"YouTube credentials refreshed and saved to {token_path}")
        return creds

    return None


def _build_credentials_browser(lang: str) -> Credentials:
    """
    Run browser-based OAuth2 flow (local dev only — requires a display).
    Saves the resulting token to credentials/token_{lang}.pickle.
    """
    secrets_path = _client_secrets_path()
    logger.info("Starting browser OAuth2 flow — a browser window will open")
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path = _token_path(lang)
    with open(token_path, "wb") as f:
        pickle.dump(creds, f)
    logger.info(f"YouTube credentials saved to {token_path}")
    return creds


def _get_youtube_client(lang: str):
    """
    Return an authenticated YouTube API client.
    Tries .env refresh token -> stored pickle -> browser OAuth (in that order).
    """
    creds = _build_credentials_from_env()
    if creds is None:
        creds = _build_credentials_from_pickle(lang)
    if creds is None:
        creds = _build_credentials_browser(lang)
    return build("youtube", "v3", credentials=creds)


def _parse_tags(tags_raw: str) -> list[str]:
    """Extract tag names (without #) from a space-or-comma-separated hashtag string."""
    return [
        t.lstrip("#").strip()
        for t in tags_raw.replace(",", " ").split()
        if t.startswith("#") and len(t) > 1
    ]


def _upload_video(youtube, body: dict, final_path: Path, episode: int) -> str:
    """
    Resumable chunked upload. Returns YouTube video ID.
    Retries transient server errors (5xx) up to 3 times per chunk.
    Raises RuntimeError on quota exceeded or permanent failure.
    """
    RETRIABLE_CODES = {500, 502, 503, 504}
    QUOTA_CODE = 403

    media = MediaFileUpload(
        str(final_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=CHUNK_SIZE,
    )
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    chunk_errors = 0
    max_chunk_errors = 3
    chunk_num = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            chunk_errors = 0  # reset on success
            if status:
                pct = int(status.resumable_progress / status.total_size * 100)
                logger.info(f"EP{episode:02d} upload progress: {pct}%")
            chunk_num += 1
        except HttpError as e:
            if e.resp.status == QUOTA_CODE:
                raise RuntimeError(
                    f"EP{episode:02d} YouTube quota exceeded. "
                    "Wait 24 hours or check Google Cloud Console quotas."
                ) from e
            if e.resp.status in RETRIABLE_CODES and chunk_errors < max_chunk_errors:
                chunk_errors += 1
                wait = 2 ** chunk_errors
                logger.warning(
                    f"EP{episode:02d} chunk {chunk_num} HTTP {e.resp.status} "
                    f"— retry {chunk_errors}/{max_chunk_errors} in {wait}s"
                )
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"EP{episode:02d} YouTube upload failed "
                    f"(HTTP {e.resp.status}): {e.content}"
                ) from e

    return response["id"]


def run(script: dict, episode: int, week: int, lang: str = "en") -> dict:
    """
    Upload ep{NN}_final_{LANG}.mp4 to the YouTube channel for this language.

    - Reads YOUTUBE_CHANNEL_ID_{LANG} from .env to verify channel is configured.
    - Builds metadata from script JSON (title, description, tags, scheduled_publish).
    - Sets privacyStatus=private + publishAt for scheduled release.
    - Saves an upload receipt JSON next to the final video.

    Args:
        script:  Parsed script dict from script_agent (must have youtube_title etc.)
        episode: Episode number 1-7
        week:    Week number
        lang:    "en" or "ta"

    Returns:
        {"success": True, "video_id": str, "video_url": str,
         "lang": str, "scheduled_publish": str}
    """
    lang = lang.lower()
    if lang not in ("en", "ta"):
        raise RuntimeError(f"EP{episode:02d} unsupported lang '{lang}'")

    ep_dir     = _episode_dir(episode, week)
    final_path = ep_dir / f"ep{episode:02d}_final_{lang.upper()}.mp4"
    receipt_path = ep_dir / f"ep{episode:02d}_upload_{lang.upper()}.json"

    # Guard: skip if already uploaded this run
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        logger.info(
            f"EP{episode:02d} [{lang.upper()}] already uploaded "
            f"-> {receipt['video_url']} (skipping)"
        )
        return {
            "success": True,
            "video_id": receipt["video_id"],
            "video_url": receipt["video_url"],
            "lang": lang,
            "scheduled_publish": receipt.get("scheduled_publish", ""),
            "skipped": True,
        }

    if not final_path.exists():
        raise RuntimeError(
            f"EP{episode:02d} final video not found: {final_path}. "
            "Run assembly_agent first."
        )

    # Validate channel is configured — explicit per-lang to prevent cross-channel uploads
    if lang == "ta":
        channel_id = os.getenv("YOUTUBE_CHANNEL_ID_TA", "")
        channel_id_key = "YOUTUBE_CHANNEL_ID_TA"
    else:
        channel_id = os.getenv("YOUTUBE_CHANNEL_ID_EN", "")
        channel_id_key = "YOUTUBE_CHANNEL_ID_EN"
    if not channel_id or "your-" in channel_id:
        raise RuntimeError(
            f"{channel_id_key} not set in .env — cannot publish [{lang.upper()}]."
        )

    # Build video metadata from script
    scheduled_publish = script.get("scheduled_publish", "")
    title       = script.get("youtube_title", f"AI Bytes EP{episode:02d} #Shorts")
    description = script.get("youtube_description", "")
    tags        = _parse_tags(script.get("tags", "#AIBytes"))

    # For scheduled publishing: privacyStatus must be "private" + publishAt set.
    # YouTube automatically makes it public at publishAt time.
    privacy = "private" if scheduled_publish else "public"

    body: dict = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": CATEGORY_ID,
            "defaultLanguage": lang,
            "defaultAudioLanguage": lang,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }
    if scheduled_publish:
        body["status"]["publishAt"] = scheduled_publish

    logger.info(f"EP{episode:02d} [{lang.upper()}] uploading to channel: {channel_id[:8]}...")
    logger.info(
        f"EP{episode:02d} [{lang.upper()}] uploading '{title}' "
        f"({final_path.stat().st_size / 1_048_576:.1f} MB) "
        f"scheduled={scheduled_publish or 'immediate'}"
    )

    youtube = _get_youtube_client(lang)
    t0 = time.monotonic()
    video_id = _upload_video(youtube, body, final_path, episode)
    upload_time = time.monotonic() - t0

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    logger.info(
        f"EP{episode:02d} [{lang.upper()}] uploaded in {upload_time:.1f}s "
        f"-> {video_url}"
    )

    # Save receipt so idempotent re-runs skip the upload
    receipt = {
        "video_id": video_id,
        "video_url": video_url,
        "lang": lang,
        "title": title,
        "scheduled_publish": scheduled_publish,
        "channel_id": channel_id,
        "upload_time_s": round(upload_time, 1),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"EP{episode:02d} [{lang.upper()}] receipt saved -> {receipt_path}")

    return {
        "success": True,
        "video_id": video_id,
        "video_url": video_url,
        "lang": lang,
        "scheduled_publish": scheduled_publish,
        "skipped": False,
    }
