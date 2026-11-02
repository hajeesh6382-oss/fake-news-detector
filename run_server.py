
"""
Run script for Advanced AI-Powered Fake News Detection System.
Launches the FastAPI backend and serves the interactive frontend on http://localhost:8000.
"""

import sys
import uvicorn
from backend.config import config

if __name__ == "__main__":
    print("=" * 70)
    print("🛡️  ADVANCED AI-POWERED FAKE NEWS DETECTION SYSTEM v2.0")
    print(f"📡  Server starting on http://{config.HOST}:{config.PORT}")
    print(f"🧠  Gemini AI API: {'Configured' if config.GEMINI_API_KEY else 'Local NLP Fallback Active'}")
    print(f"🔍  Fact-Checking API: {'Configured' if config.GOOGLE_FACTCHECK_API_KEY else 'RSS & Search Engine Active'}")
    print(f"💾  Database: {config.DATABASE_URL}")
    print("=" * 70)

    try:
        uvicorn.run(
            "backend.main:app",
            host=config.HOST,
            port=config.PORT,
            reload=config.DEBUG,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)
