import re
from typing import Dict, Any, Optional
import requests
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
except ImportError:
    YouTubeTranscriptApi = None
    TranscriptsDisabled = Exception
    NoTranscriptFound = Exception
    VideoUnavailable = Exception
from backend.config import config

YOUTUBE_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)

def extract_youtube_video_id(url: str) -> Optional[str]:
    match = YOUTUBE_REGEX.search(url.strip())
    return match.group(1) if match else None

def extract_youtube_content(url: str) -> Dict[str, Any]:
    """
    Extracts metadata, title, and speech transcript for YouTube video URLs.
    Does not fake or simulate transcripts.
    """
    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL. Please provide a standard YouTube video link (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...).")

    # 1. Fetch Video Metadata via YouTube oEmbed
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    title = f"YouTube Video ({video_id})"
    author_name = "YouTube Creator"
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    try:
        resp = requests.get(oembed_url, timeout=config.REQUEST_TIMEOUT)
        if resp.ok:
            meta = resp.json()
            title = meta.get("title", title)
            author_name = meta.get("author_name", author_name)
            thumbnail_url = meta.get("thumbnail_url", thumbnail_url)
    except Exception as e:
        # Fall back to default title if oEmbed fails
        pass

    # 2. Extract Transcript / Captions
    transcript_text = ""
    transcript_segments = []
    has_transcript = False
    warnings = []

    raw_segments = []
    if YouTubeTranscriptApi is not None:
        try:
            api_instance = YouTubeTranscriptApi()
            if hasattr(api_instance, "fetch"):
                fetched = api_instance.fetch(video_id, languages=["en", "en-US", "en-GB"])
                raw_segments = list(fetched)
            elif hasattr(api_instance, "list"):
                t_list = api_instance.list(video_id)
                t_obj = t_list.find_transcript(["en", "en-US", "en-GB"])
                raw_segments = list(t_obj.fetch())
        except Exception:
            pass

        if not raw_segments:
            try:
                if hasattr(YouTubeTranscriptApi, "get_transcript"):
                    raw_segments = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
                elif hasattr(YouTubeTranscriptApi, "list_transcripts"):
                    t_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    t_obj = t_list.find_transcript(["en", "en-US", "en-GB"])
                    raw_segments = list(t_obj.fetch())
            except Exception:
                pass

    if raw_segments:
        cleaned_segments = []
        full_parts = []
        for item in raw_segments:
            txt = ""
            start_sec = 0
            if isinstance(item, dict):
                txt = item.get("text", "")
                start_sec = int(item.get("start", 0))
            elif hasattr(item, "text"):
                txt = getattr(item, "text", "")
                start_sec = int(getattr(item, "start", 0))

            seg_text = txt.replace("\n", " ").strip()
            if seg_text:
                mins, secs = divmod(start_sec, 60)
                timestamp_str = f"{mins:02d}:{secs:02d}"
                cleaned_segments.append({
                    "start": timestamp_str,
                    "seconds": start_sec,
                    "text": seg_text
                })
                full_parts.append(seg_text)

        if full_parts:
            transcript_text = " ".join(full_parts)
            transcript_segments = cleaned_segments[:30]
            has_transcript = True

    if not transcript_text:
        transcript_text = title
        warnings.append("Captions are disabled or unavailable for this video; audited using video headline & metadata.")

    summary_excerpt = transcript_text[:500] + ("..." if len(transcript_text) > 500 else "")

    return {
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "video_id": video_id,
        "title": title,
        "author": author_name,
        "thumbnail_url": thumbnail_url,
        "transcript": transcript_text,
        "text": transcript_text,
        "summary": summary_excerpt,
        "transcript_segments": transcript_segments,
        "has_transcript": has_transcript,
        "word_count": len(transcript_text.split()),
        "domain": "youtube.com",
        "site_name": "YouTube",
        "warnings": warnings
    }
