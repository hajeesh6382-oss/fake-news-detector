import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")
    GOOGLE_FACTCHECK_API_KEY: str = os.getenv("GOOGLE_FACTCHECK_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:////tmp/fake_news.db" if os.getenv("VERCEL") else "sqlite:///./fake_news.db"
    )

    # Network & Security
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "10"))
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 VeritasNewsEngine/2.0"
    )

    # Major International News Outlets (Domain & Brand Name)
    INTERNATIONAL_SOURCES: Dict[str, str] = {
        "bbc.com": "BBC News",
        "bbc.co.uk": "BBC News",
        "reuters.com": "Reuters",
        "apnews.com": "Associated Press",
        "cnn.com": "CNN",
        "aljazeera.com": "Al Jazeera",
        "theguardian.com": "The Guardian",
        "france24.com": "France 24",
        "dw.com": "DW News",
        "nytimes.com": "The New York Times",
        "washingtonpost.com": "The Washington Post",
        "bloomberg.com": "Bloomberg"
    }

    # Major Indian News Outlets (Domain & Brand Name)
    INDIAN_SOURCES: Dict[str, str] = {
        "thehindu.com": "The Hindu",
        "indianexpress.com": "The Indian Express",
        "timesofindia.indiatimes.com": "Times of India",
        "ndtv.com": "NDTV",
        "hindustantimes.com": "Hindustan Times",
        "indiatoday.in": "India Today",
        "news18.com": "News18",
        "aninews.in": "ANI News"
    }

    # Fact-Checking Organizations
    FACT_CHECK_SOURCES: Dict[str, str] = {
        "pib.gov.in": "PIB Fact Check",
        "boomlive.in": "BOOM Live",
        "altnews.in": "Alt News",
        "snopes.com": "Snopes",
        "factcheck.org": "FactCheck.org",
        "politifact.com": "PolitiFact"
    }

    @property
    def ALL_TRUSTED_DOMAINS(self) -> List[str]:
        return list(self.INTERNATIONAL_SOURCES.keys()) + list(self.INDIAN_SOURCES.keys()) + list(self.FACT_CHECK_SOURCES.keys()) + [
            "who.int", "cdc.gov", "un.org", "gov.in", "nic.in"
        ]

    # Suspicious domain indicators
    SUSPICIOUS_TLDS: List[str] = [
        ".xyz", ".top", ".buzz", ".click", ".free", ".tk", ".ml", ".ga", ".cf"
    ]

config = Config()
