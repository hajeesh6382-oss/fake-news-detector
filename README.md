# 🛡️ Veritas AI &ndash; Advanced AI-Powered Fake News Detection System

An enterprise-grade, intelligent News & Video Fact Verification Platform. Combines Natural Language Processing (NLP), automated claim extraction, YouTube transcript inspection, and real-time cross-referencing against Google Fact Check Explorer, Reuters, BBC, The Hindu, Snopes, and indexed global archives.

[![Live Web Application](https://img.shields.io/badge/Live%20Platform-fake--news--detector--tau--roan.vercel.app-success?style=for-the-badge&logo=vercel)](https://fake-news-detector-tau-roan.vercel.app)
[![FastAPI Backend](https://img.shields.io/badge/Backend-FastAPI%20%26%20Python%203.14-009688?style=for-the-badge&logo=fastapi)](https://github.com/hajeesh6382-oss/fake-news-detector)
[![SQLite Database](https://img.shields.io/badge/Database-SQLite%20Persistent%20History-003B57?style=for-the-badge&logo=sqlite)](https://github.com/hajeesh6382-oss/fake-news-detector)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

---

## 🌟 Key Features

### 1. 🌐 URL-Based News Verification
- Input any live article link from major outlets (e.g., **BBC News, The Hindu, Reuters, CNN, Times of India, Associated Press**).
- Safe SSRF (Server-Side Request Forgery) protection prevents unauthorized requests to internal network addresses.
- Automatically extracts article headlines, publication dates, author metadata, and body content.

### 2. 🎥 YouTube Video Fact Verification
- Supports standard YouTube links, `youtu.be` shortcuts, and YouTube Shorts.
- Pulls authentic video metadata (channel, title, duration) and fetches real speech transcripts via `youtube-transcript-api`.
- Extracts spoken claims directly from audio transcripts and audits them against fact-checking repositories.
- **Zero Hallucination Guarantee:** If captions are disabled or unavailable, the system transparently notifies the user rather than faking a transcript.

### 3. 🧠 NLP & Automated Claim Extraction
- Linguistic parsing identifies assertive factual statements, statistics, and verifiable assertions from article bodies.
- **Headline Discrepancy Detection:** Analyzes alignment between sensationalist headlines and article content to catch deceptive clickbait.

### 4. 🔍 Real-Time Multi-Source Fact Checking
- Integrates with **Google Fact Check Explorer API**, **Snopes**, **FactCheck.org**, **PolitiFact**, and verified RSS feeds.
- Retrieves genuine supporting and contradicting evidence with real clickable links and ratings.
- **Temporal Outdated Information Detection:** Detects if a recirculated story refers to events from past years being passed off as breaking news.

### 5. 📊 Comprehensive Evidence Dashboard
- Color-coded multi-class verdicts:
  - 🟢 **REAL NEWS** &ndash; Corroborated by verified reporting and institutional attribution.
  - 🚨 **POTENTIALLY FAKE** &ndash; Contradicted by accredited fact-checkers or dense with unverified clickbait.
  - ⚠️ **MISLEADING** &ndash; Significant divergence between headline claims and underlying facts.
  - ⏰ **OUTDATED INFORMATION** &ndash; Historical facts recirculated out of chronological context.
  - ⚖️ **UNVERIFIED** &ndash; *Ethical Principle:* News is never declared fake simply because it has not yet appeared in mainstream headlines.
- Visual confidence score gauge (distinguishing confidence from factual certainty).
- Supporting evidence cards, contradicting fact-check cards, and audited source badges.

### 6. 💾 Persistent SQLite Database
- Stores complete verification dossiers: URL, headline, extracted claims, evidence links, classification, confidence score, and timestamp.
- Full interactive History tab with multi-class filtering, keyword search, and one-click report loading.

---

## 🏗️ System Architecture

```
fake-news-detector/
├── backend/
│   ├── __init__.py
│   ├── config.py                 # Environment settings & trusted domains registry
│   ├── main.py                   # FastAPI REST API & SPA static file serving
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py                 # SQLite SQLAlchemy database models & CRUD
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── security.py           # SSRF protection & private IP filter
│   │   ├── url_extractor.py      # Article extraction (BeautifulSoup4)
│   │   └── youtube_extractor.py  # YouTube metadata & captions extraction
│   ├── nlp/
│   │   ├── __init__.py
│   │   ├── claim_extractor.py    # Factual claim parsing & headline alignment
│   │   └── sentiment_analyzer.py # Clickbait, sensationalism & attribution scoring
│   ├── fact_checking/
│   │   ├── __init__.py
│   │   └── factcheck_engine.py   # Google Fact Check & verified news queries
│   └── classifier/
│       ├── __init__.py
│       └── ai_classifier.py      # Gemini LLM & high-precision local NLP engine
├── index.html                    # Responsive AI SaaS Dashboard (6 views)
├── style.css                     # Premium Glassmorphism UI stylesheet
├── app.js                        # Client-side router, API controller & heuristics
├── run_server.py                 # Single-command application launcher
├── fake_news.db                  # Persistent SQLite database
├── .env.example                  # Environment configuration template
└── README.md                     # System documentation
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Web browser (Chrome, Edge, Firefox, Safari)

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/hajeesh6382-oss/fake-news-detector.git
cd fake-news-detector
pip install -r requirements.txt # Or: pip install fastapi uvicorn requests beautifulsoup4 youtube-transcript-api sqlalchemy python-dotenv
```

### 3. Configuration (Optional API Keys)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

```ini
# Optional: Google Gemini API Key for deep LLM claim analysis
# Obtain free from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Google Fact Check Tools API Key
GOOGLE_FACTCHECK_API_KEY=your_factcheck_api_key_here

# Network Settings
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./fake_news.db
```

> **Note:** The platform operates **100% offline and functional** even without external API keys using its built-in local NLP classification engine and open news indexes.

### 4. Run the Platform

Start both the FastAPI backend and interactive web interface with a single command:

```bash
python run_server.py
```

Then open your browser to:
👉 **`http://localhost:8000`**

---

## 📡 REST API Documentation

The FastAPI backend exposes the following structured endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health check and active AI model capabilities |
| `GET` | `/api/sources` | Audited registry of fact-checkers and news wire services |
| `POST` | `/api/verify/url` | Ingests news URL, performs SSRF check, extracts body & claims, verifies against evidence |
| `POST` | `/api/verify/youtube` | Parses YouTube link, extracts transcript/captions, audits spoken assertions |
| `POST` | `/api/verify/text` | Direct text & headline verification using NLP and fact-checking engines |
| `GET` | `/api/history` | Retrieves stored verification records from SQLite database |
| `GET` | `/api/history/{id}` | Retrieves full verification dossier for a specific record |
| `DELETE` | `/api/history/{id}` | Deletes an individual verification record |
| `DELETE` | `/api/history` | Clears all verification history from database |

Interactive Swagger API documentation is available at:
👉 **`http://localhost:8000/docs`**

---

## 🌐 Live Cloud Deployment

- **Vercel Host Link:** [https://fake-news-detector-tau-roan.vercel.app](https://fake-news-detector-tau-roan.vercel.app)
- **GitHub Repository:** [https://github.com/hajeesh6382-oss/fake-news-detector](https://github.com/hajeesh6382-oss/fake-news-detector)

---

## 🛡️ License

This project is licensed under the MIT License.
