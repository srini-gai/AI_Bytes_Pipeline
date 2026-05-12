# YouTube Skill — AI Bytes

> YouTube Data API v3 patterns, OAuth2 setup, scheduling, and metadata rules.

---

## Auth — OAuth2 Refresh Token (no browser on VPS)

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

def get_youtube_client():
    """Build authenticated YouTube client using refresh token."""
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)
```

---

## Upload a Video

```python
from googleapiclient.http import MediaFileUpload

def upload_video(youtube, video_path: str, title: str, description: str,
                 tags: list[str], scheduled_time: str) -> str:
    """
    Upload video and schedule publish. Returns YouTube video ID.

    Args:
        scheduled_time: ISO 8601 UTC string e.g. "2026-05-12T02:30:00Z"
    """
    body = {
        "snippet": {
            "title": title,           # must end with #Shorts
            "description": description,
            "tags": tags,
            "categoryId": "22",       # People & Blogs
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": scheduled_time,
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5  # 5MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()

    return response["id"]
```

---

## Schedule Calculation

```python
from datetime import datetime, timedelta
import pytz

def get_publish_schedule(start_date: str, publish_time_utc: str, count: int = 7) -> list[str]:
    """
    Generate one publish time per day starting from start_date.

    Args:
        start_date: "YYYY-MM-DD" — first Monday of the week
        publish_time_utc: "HH:MM" — 8AM IST = "02:30"
        count: Number of slots (7 for one per day Mon–Sun)

    Returns:
        List of ISO 8601 UTC strings
    """
    hour, minute = map(int, publish_time_utc.split(":"))
    base = datetime.strptime(start_date, "%Y-%m-%d").replace(
        hour=hour, minute=minute, second=0, microsecond=0,
        tzinfo=pytz.UTC
    )
    return [(base + timedelta(days=i)).strftime("%Y-%m-%dT%H:%M:%SZ") for i in range(count)]
```

---

## Metadata Rules

| Field | Rule |
|-------|------|
| Title | Must end with `#Shorts` |
| Description | Include full hashtag block from script JSON |
| Tags | Split `tags` field from script JSON by space |
| Privacy | Upload as `private`, schedule via `publishAt` |
| Category | `22` (People & Blogs) |
| Made for kids | `false` |

---

## Shorts Requirements

- Title ends with `#Shorts`
- Video is vertical: 1080×1920
- Duration: under 60 seconds (target 58–60s)
- Upload via resumable upload (large file support)

---

## Error Handling

```python
from googleapiclient.errors import HttpError

def upload_with_retry(youtube, video_path, body, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            return upload_video(youtube, video_path, **body)
        except HttpError as e:
            if e.resp.status in [500, 503] and attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise
```
