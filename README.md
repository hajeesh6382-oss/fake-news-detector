# 🛡️ Fake News Detector

An educational, rule-based credibility analysis application designed to identify sensationalist patterns, red-flag keywords, and authoritative citations in news headlines and social statements.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-fake--news--detector--tau--roan.vercel.app-success?style=for-the-badge&logo=vercel)](https://fake-news-detector-tau-roan.vercel.app)
[![GitHub Repository](https://img.shields.io/badge/GitHub-hajeesh6382--oss%2Ffake--news--detector-181717?style=for-the-badge&logo=github)](https://github.com/hajeesh6382-oss/fake-news-detector)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

---

## 🌟 Key Features

- **Heuristic Rule Engine**: Computes suspicion and credibility metrics using keyword lexicons and linguistic stylistics.
- **Visual Keyword Highlights**: Automatically highlights sensationalist phrases (red) and credible citations (green) right within the input text.
- **Real-Time Analysis**: Optional real-time typing mode for immediate instant feedback.
- **Interactive Scoring Meter**: Visualizes balance and confidence ratios between suspicious indicators and institutional citations.
- **Persistent History**: Stores past checks with click-to-reload functionality, filtering by verdict (Fake, Likely Real, Uncertain), and clear actions.
- **Theme Support**: Seamless Dark Mode and Light Mode with system preference detection and localStorage persistence.
- **Dual Deployment Options**: Run as a modern web app on Vercel or locally with zero dependencies using Python's built-in standard library.

---

## 🔬 How the Detection Logic Works

The analyzer evaluates any headline or statement across three core heuristic layers:

1. **Sensational Red Flags (+1 Suspicion each)**:
   - Phrases: `shocking`, `you won't believe`, `miracle`, `secret`, `exposed`, `hoax`, `conspiracy`, `100% cure`, `share before`, `forward this`, `breaking!!!`, `they don't want you to know`, `free money`, `instant cure`, `leaked`, `banned`, `doctors hate`, `guaranteed`, `viral`, `urgent`.
2. **Authoritative Citations (+1 Credibility each)**:
   - Phrases: `according to`, `official`, `government`, `ministry`, `report`, `published`, `research`, `study`, `confirmed`, `announced`, `police`, `university`, `officials`, `statement`, `data`, `survey`, `press conference`, `court`, `department`, `minister`.
3. **Stylistic Penalties (+1 Suspicion each)**:
   - Excessive punctuation (`!!` or `??`).
   - Heavy capitalization (>70% uppercase letters for texts with 10+ letters).

### Decision Rules
- **Suspicion Score > Credibility Score**: `FAKE NEWS` 🚨
- **Credibility Score > Suspicion Score**: `LIKELY REAL NEWS` ✅
- **Equal Scores**: `UNCERTAIN` ⚖️

> **Disclaimer**: This is a rule-based educational prototype. Predictions are preliminary heuristic guesses and do not replace professional journalistic fact-checking.

---

## 🚀 Running Locally

### Option 1: Standalone Python Server (Zero Dependencies)

```bash
python fake_news_website.py
```
Then open your browser to `http://localhost:8000`.

### Option 2: Live Web Version

Simply open `index.html` in any browser, or use a local dev server:

```bash
npx serve .
```

---

## 🌐 Deployment

The web app is deployed on **Vercel** and source-controlled on **GitHub**.
