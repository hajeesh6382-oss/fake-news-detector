import re
from typing import Dict, Any, Optional
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
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

    try:
        # Fetch transcript using YouTubeTranscriptApi
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Try finding manual English transcript first, then generated English, then any
            try:
                transcript_obj = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except Exception:
                # Find any generated or available language
                transcript_obj = transcript_list.find_generated_transcript(['en', 'en-US'])
            
            raw_segments = transcript_obj.fetch()
        except Exception:
            # Fallback to direct get_transcript
            raw_segments = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])

        cleaned_segments = []
        full_parts = []
        for item in raw_segments:
            seg_text = item.get("text", "").replace("\n", " ").strip()
            if seg_text:
                start_sec = int(item.get("start", 0))
                mins, secs = divmod(start_sec, 60)
                timestamp_str = f"{mins:02d}:{secs:02d}"
                cleaned_segments.append({
                    "start": timestamp_str,
                    "seconds": start_sec,
                    "text": seg_text
                })
                full_parts.append(seg_text)

        transcript_text = " ".join(full_parts)
        transcript_segments = cleaned_segments[:30]  # Store top 30 segments for UI

    except TranscriptsDisabled:
        raise ValueError(
            f"Transcripts are disabled by the creator for YouTube video '{title}'. "
            "To verify this claim, copy the headline or specific spoken claim into the text verification tab."
        )
    except NoTranscriptFound:
        raise ValueError(
            f"No English subtitles or transcripts found for YouTube video '{title}'. "
            "Verification requires accessible spoken or text content."
        )
    except VideoUnavailable:
        raise ValueError("This YouTube video is private, removed, or unavailable.")
    except Exception as e:
        raise ValueError(
            f"Could not retrieve video transcript: {str(e)}. "
            "You can test the video's claim directly by typing or pasting it into the Text Verification tab."
        )

    if not transcript_text:
        raise ValueError("Video transcript is empty or could not be decoded.")

    # Generate excerpt
    summary_excerpt = transcript_text[:500] + ("..." if len(transcript_text) > 500 else "")

    return {
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "video_id": video_id,
        "title": title,
        "author": author_name,
        "thumbnail_url": thumbnail_url,
        "text": transcript_text,
        "summary": summary_excerpt,
        "transcript_segments": transcript_segments,
        "word_count": len(transcript_text.split()),
        "domain": "youtube.com",
        "site_name": "YouTube"
    }
