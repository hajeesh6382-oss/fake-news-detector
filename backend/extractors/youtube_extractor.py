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

# Accredited news publishers operating official YouTube channels
KNOWN_NEWS_CHANNELS = [
    {"name": "BBC News", "domain": "bbc.com", "patterns": [r"\bbbc\b", r"\bbbc news\b", r"\bbbc world\b"]},
    {"name": "Reuters", "domain": "reuters.com", "patterns": [r"\breuters\b"]},
    {"name": "Associated Press", "domain": "apnews.com", "patterns": [r"\bassociated press\b", r"\bap news\b", r"\bap archive\b"]},
    {"name": "The Hindu", "domain": "thehindu.com", "patterns": [r"\bthe hindu\b", r"\bthehindu\b"]},
    {"name": "CNN", "domain": "cnn.com", "patterns": [r"\bcnn\b", r"\bcnn-news18\b"]},
    {"name": "NDTV", "domain": "ndtv.com", "patterns": [r"\bndtv\b", r"\bndtv 24x7\b", r"\bndtv india\b"]},
    {"name": "The Indian Express", "domain": "indianexpress.com", "patterns": [r"\bindian express\b", r"\bthe indian express\b"]},
    {"name": "Times of India", "domain": "timesofindia.indiatimes.com", "patterns": [r"\btimes of india\b", r"\btoi\b", r"\btimes now\b"]},
    {"name": "Hindustan Times", "domain": "hindustantimes.com", "patterns": [r"\bhindustan times\b"]},
    {"name": "India Today", "domain": "indiatoday.in", "patterns": [r"\bindia today\b", r"\baaj tak\b"]},
    {"name": "The Guardian", "domain": "theguardian.com", "patterns": [r"\bguardian\b", r"\bthe guardian\b"]},
    {"name": "Al Jazeera", "domain": "aljazeera.com", "patterns": [r"\bal jazeera\b", r"\baj english\b"]},
    {"name": "France 24", "domain": "france24.com", "patterns": [r"\bfrance 24\b"]},
    {"name": "DW News", "domain": "dw.com", "patterns": [r"\bdw news\b", r"\bdeutsche welle\b", r"\bdw\b"]},
    {"name": "Sky News", "domain": "skynews.com", "patterns": [r"\bsky news\b"]},
    {"name": "ABC News", "domain": "abcnews.go.com", "patterns": [r"\babc news\b"]},
    {"name": "CBS News", "domain": "cbsnews.com", "patterns": [r"\bcbs news\b"]},
    {"name": "NBC News", "domain": "nbcnews.com", "patterns": [r"\bnbc news\b"]},
    {"name": "Bloomberg", "domain": "bloomberg.com", "patterns": [r"\bbloomberg\b"]},
    {"name": "CNBC", "domain": "cnbc.com", "patterns": [r"\bcnbc\b"]},
    {"name": "ANI News", "domain": "aninews.in", "patterns": [r"\bani news\b", r"\bani\b"]},
    {"name": "WION", "domain": "wionews.com", "patterns": [r"\bwion\b"]}
]

def extract_youtube_video_id(url: str) -> Optional[str]:
    match = YOUTUBE_REGEX.search(url.strip())
    return match.group(1) if match else None

def extract_youtube_content(url: str) -> Dict[str, Any]:
    """
    Extracts metadata, title, and speech transcript for YouTube video URLs.
    Recognizes accredited news channels and cleans headlines for accurate fact checking.
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
    except Exception:
        # Fall back to default title if oEmbed is unreachable
        pass

    # Clean headline for accurate cross-platform search (strip brand name & noisy tags)
    clean_title = re.sub(
        r"\s*[-|–—]\s*(?:BBC News|BBC|CNN|Reuters|The Hindu|NDTV|Times Now|Associated Press|Sky News|France 24|DW News|India Today|Hindustan Times|The Guardian|Al Jazeera|ABC News|CBS News|NBC News|Bloomberg|WION|ANI).*$",
        "",
        title,
        flags=re.I
    ).strip()
    clean_title = re.sub(r"\[.*?\]|\(.*?\)", "", clean_title).strip()
    clean_title = re.sub(r"^(?:LIVE|WATCH|BREAKING NEWS|UPDATE|EXCLUSIVE)\s*[:|-]\s*", "", clean_title, flags=re.I).strip()
    if not clean_title or len(clean_title) < 5:
        clean_title = title

    # Detect recognized news organizations from author or title
    publisher = author_name
    domain = "youtube.com"
    is_trusted = False

    for outlet in KNOWN_NEWS_CHANNELS:
        for pat in outlet["patterns"]:
            if re.search(pat, author_name, re.I) or re.search(pat, title, re.I):
                publisher = outlet["name"]
                domain = outlet["domain"]
                is_trusted = True
                break
        if is_trusted:
            break

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
        transcript_text = f"{clean_title}. News report published by channel {author_name}."
        if not is_trusted:
            warnings.append("Captions are disabled or unavailable for this video; audited using video headline & metadata.")

    summary_excerpt = transcript_text[:500] + ("..." if len(transcript_text) > 500 else "")

    return {
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "video_id": video_id,
        "title": title,
        "clean_headline": clean_title,
        "author": author_name,
        "publisher": publisher,
        "domain": domain,
        "is_trusted": is_trusted,
        "thumbnail_url": thumbnail_url,
        "transcript": transcript_text,
        "text": transcript_text,
        "summary": summary_excerpt,
        "transcript_segments": transcript_segments,
        "has_transcript": has_transcript,
        "word_count": len(transcript_text.split()),
        "site_name": "YouTube",
        "warnings": warnings
    }
