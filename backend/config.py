import os
from typing import List
from dotenv import load_dotenv

# Load .env file if available
load_dotenv()

class Config:
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_FACTCHECK_API_KEY: str = os.getenv("GOOGLE_FACTCHECK_API_KEY", "")

    # Database (In Vercel serverless environment, use writable /tmp)
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

    # Trusted News & Fact-Checking Domains
    TRUSTED_DOMAINS: List[str] = [
        "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com", "thehindu.com",
        "ndtv.com", "indiatoday.in", "indianexpress.com", "hindustantimes.com",
        "timesofindia.indiatimes.com", "cnn.com", "nytimes.com",
        "washingtonpost.com", "theguardian.com", "bloomberg.com", "aljazeera.com",
        "factcheck.org", "snopes.com", "politifact.com", "pib.gov.in",
        "who.int", "cdc.gov", "un.org"
    ]

    # Suspicious domain indicators
    SUSPICIOUS_TLDS: List[str] = [
        ".xyz", ".top", ".buzz", ".click", ".free", ".tk", ".ml", ".ga", ".cf"
    ]

config = Config()
