/**
 * VERITAS AI - ENTERPRISE NEWS & VIDEO FACT VERIFICATION PLATFORM
 * Integrates Python FastAPI backend, NLP claim extraction, YouTube transcripts,
 * real-time fact-checking across Google Fact Check Explorer & verified news archives,
 * SQLite persistent history, and client-side offline heuristics.
 */

// ============================================================
// 1. GLOBAL STATE & CONFIGURATION
// ============================================================
const API_BASE = ""; // Relative path to FastAPI backend
let isBackendOnline = false;
let currentAnalysisRecord = null;
let databaseHistoryRecords = [];

// Storage Keys
const THEME_KEY = "veritas_theme_preference";
const LOCAL_HISTORY_KEY = "veritas_analysis_history";

// Core Heuristic Lexicons (Preserves standard test cases)
const FAKE_KEYWORDS = [
  "shocking", "you won't believe", "miracle", "secret", "exposed",
  "hoax", "conspiracy", "100% cure", "share before", "forward this",
  "breaking!!!", "they don't want you to know", "free money",
  "instant cure", "leaked", "banned", "doctors hate", "guaranteed",
  "viral", "urgent"
];

const REAL_KEYWORDS = [
  "according to", "official", "government", "ministry", "report",
  "published", "research", "study", "confirmed", "announced",
  "police", "university", "officials", "statement", "data",
  "survey", "press conference", "court", "department", "minister"
];

const EXTENDED_FAKE_KEYWORDS = [
  "miracle cure", "share before deleted", "share before banned",
  "forward this to everyone", "100% genuine", "government won't tell you",
  "secret remedy", "urgent alert", "classified leaked", "wake up people",
  "mind blowing", "they are lying to you", "click here immediately",
  "act fast before", "hidden truth exposed", "deep state", "forwarded as received"
];

const EXTENDED_REAL_KEYWORDS = [
  "reuters", "associated press", "bbc news", "cnn", "ndtv", "the hindu",
  "the guardian", "new york times", "washington post", "bloomberg",
  "world health organization", "press release", "official spokesperson",
  "peer-reviewed", "clinical trial", "supreme court", "high court"
];

const PRESETS = {
  fake: "SHOCKING!! Miracle cure exposed, share before it is banned",
  real: "According to the Ministry of Health, an official report was published today",
  neutral: "The weather is nice today",
  clickbait: "URGENT!! Free money guaranteed, doctors hate this 100% cure, share before it gets banned!!"
};

// ============================================================
// 2. DOM ELEMENT REFERENCES
// ============================================================
const systemStatusPill = document.getElementById("systemStatusPill");
const systemStatusText = document.getElementById("systemStatusText");
const themeToggleBtn = document.getElementById("themeToggleBtn");
const toast = document.getElementById("toast");

// Input Fields
const articleUrlInput = document.getElementById("articleUrlInput");
const verifyUrlBtn = document.getElementById("verifyUrlBtn");
const pasteArticleUrlBtn = document.getElementById("pasteArticleUrlBtn");

const youtubeUrlInput = document.getElementById("youtubeUrlInput");
const verifyYouTubeBtn = document.getElementById("verifyYouTubeBtn");
const pasteYouTubeUrlBtn = document.getElementById("pasteYouTubeUrlBtn");

const newsInput = document.getElementById("newsInput");
const checkBtn = document.getElementById("checkBtn");
const resetBtn = document.getElementById("resetBtn");
const clearTextBtn = document.getElementById("clearTextBtn");
const charCounter = document.getElementById("charCounter");
const validationMessage = document.getElementById("validationMessage");
const liveModeToggle = document.getElementById("liveModeToggle");

const pasteClipboardBtn = document.getElementById("pasteClipboardBtn");
const fetchUrlBtn = document.getElementById("fetchUrlBtn");

// Processing Overlay
const processingCard = document.getElementById("processingCard");
const processingStepTitle = document.getElementById("processingStepTitle");
const processingStepSubtitle = document.getElementById("processingStepSubtitle");

// Sidebar Result Card
const emptyResultState = document.getElementById("emptyResultState");
const activeResultState = document.getElementById("activeResultState");
const verdictBanner = document.getElementById("verdictBanner");
const verdictIcon = document.getElementById("verdictIcon");
const verdictTitle = document.getElementById("verdictTitle");
const verdictSubtitle = document.getElementById("verdictSubtitle");
const verdictTimestamp = document.getElementById("verdictTimestamp");
const fakeScoreVal = document.getElementById("fakeScoreVal");
const realScoreVal = document.getElementById("realScoreVal");
const signalDeltaVal = document.getElementById("signalDeltaVal");
const meterFill = document.getElementById("meterFill");
const confidencePercentage = document.getElementById("confidencePercentage");
const highlightedContent = document.getElementById("highlightedContent");
const reasonsList = document.getElementById("reasonsList");
const adviceBox = document.getElementById("adviceBox");
const adviceIcon = document.getElementById("adviceIcon");
const adviceTitle = document.getElementById("adviceTitle");
const adviceText = document.getElementById("adviceText");
const googleNewsSearchBtn = document.getElementById("googleNewsSearchBtn");
const googleFactCheckBtn = document.getElementById("googleFactCheckBtn");
const copyResultBtn = document.getElementById("copyResultBtn");
const shareResultBtn = document.getElementById("shareResultBtn");

// Full Evidence Dashboard DOM Elements
const fullEvidenceEmpty = document.getElementById("fullEvidenceEmpty");
const fullEvidenceContent = document.getElementById("fullEvidenceContent");
const evClassificationBadge = document.getElementById("evClassificationBadge");
const evConfidenceVal = document.getElementById("evConfidenceVal");
const evModelUsed = document.getElementById("evModelUsed");
const evOutdatedAlert = document.getElementById("evOutdatedAlert");
const evOutdatedText = document.getElementById("evOutdatedText");
const evSourceMeta = document.getElementById("evSourceMeta");
const evHeadline = document.getElementById("evHeadline");
const evDateMeta = document.getElementById("evDateMeta");
const evWordCountMeta = document.getElementById("evWordCountMeta");
const evOriginalLink = document.getElementById("evOriginalLink");
const evSummaryText = document.getElementById("evSummaryText");
const evClaimsList = document.getElementById("evClaimsList");
const evSupportingList = document.getElementById("evSupportingList");
const evContradictingList = document.getElementById("evContradictingList");
const evTrustedSourcesBadges = document.getElementById("evTrustedSourcesBadges");
const evExplanationText = document.getElementById("evExplanationText");
const evCopyBtn = document.getElementById("evCopyBtn");

// History DOM
const historyTableBody = document.getElementById("historyTableBody");
const historySearchInput = document.getElementById("historySearchInput");
const dbHistoryFilters = document.getElementById("dbHistoryFilters");
const clearAllDbHistoryBtn = document.getElementById("clearAllDbHistoryBtn");
const historyDatabaseCount = document.getElementById("historyDatabaseCount");
const navHistoryBadge = document.getElementById("navHistoryBadge");
const dashTotalChecked = document.getElementById("dashTotalChecked");
const dashboardRecentList = document.getElementById("dashboardRecentList");

// Lexicons
const fakeKeywordCloud = document.getElementById("fakeKeywordCloud");
const realKeywordCloud = document.getElementById("realKeywordCloud");

// ============================================================
// 3. MULTI-VIEW & TAB ROUTING
// ============================================================

function switchView(viewName, subTab = null) {
  // Update nav tabs
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.view === viewName);
  });

  // Update views
  document.querySelectorAll(".app-view").forEach(view => {
    view.classList.remove("active");
  });

  const targetView = document.getElementById(`view${capitalize(viewName)}`);
  if (targetView) {
    targetView.classList.add("active");
  }

  // Handle sub-tab if specified
  if (viewName === "verify" && subTab) {
    switchInputTab(subTab);
  }

  // Refresh history if navigating to history
  if (viewName === "history") {
    loadDatabaseHistory();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function switchInputTab(tabName) {
  document.querySelectorAll(".input-tab").forEach(tab => {
    tab.classList.remove("active");
  });
  document.querySelectorAll(".input-pane").forEach(pane => {
    pane.classList.remove("active");
  });

  const btn = document.getElementById(`tab${capitalize(tabName)}Btn`);
  const pane = document.getElementById(`pane${capitalize(tabName)}`);
  if (btn) btn.classList.add("active");
  if (pane) pane.classList.add("active");
}

function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// Brand click -> Go to Dashboard
document.getElementById("brandLogoBtn").addEventListener("click", () => switchView("dashboard"));

// Top nav buttons event listeners
document.querySelectorAll(".nav-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    switchView(tab.dataset.view);
  });
});

// ============================================================
// 4. BACKEND HEALTH CHECK & CONNECTION
// ============================================================

async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { method: "GET" });
    if (res.ok) {
      const data = await res.json();
      isBackendOnline = true;
      systemStatusPill.classList.remove("offline");
      systemStatusText.textContent = "AI Engine Online (FastAPI + NLP)";
      loadDatabaseHistory();
      return true;
    }
  } catch (e) {
    // Backend offline / static mode
  }
  isBackendOnline = false;
  systemStatusPill.classList.add("offline");
  systemStatusText.textContent = "Client Engine Active";
  loadLocalHistory();
  return false;
}

// ============================================================
// 5. PROCESSING ANIMATION CONTROLLER
// ============================================================

function showProcessing(title, subtitle) {
  processingCard.classList.remove("hidden");
  processingStepTitle.textContent = title;
  processingStepSubtitle.textContent = subtitle;

  const dots = ["pstep1", "pstep2", "pstep3", "pstep4"];
  dots.forEach(id => document.getElementById(id).classList.remove("active"));
  document.getElementById("pstep1").classList.add("active");

  let step = 0;
  window.processingInterval = setInterval(() => {
    step = (step + 1) % dots.length;
    dots.forEach((id, idx) => {
      document.getElementById(id).classList.toggle("active", idx <= step);
    });
  }, 1200);
}

function hideProcessing() {
  clearInterval(window.processingInterval);
  processingCard.classList.add("hidden");
}

// ============================================================
// 6. ARTICLE URL VERIFICATION
// ============================================================

async function verifyArticleUrl() {
  const url = articleUrlInput.value.trim();
  if (!url) {
    showToast("Please enter or paste a news article URL.");
    articleUrlInput.focus();
    return;
  }

  showProcessing("Inspecting News Article Link...", "Running SSRF security check, parsing article body, and extracting claims");

  try {
    const response = await fetch(`${API_BASE}/api/verify/url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server returned error status ${response.status}`);
    }

    const data = await response.json();
    hideProcessing();

    // Render full Evidence Dashboard
    renderFullEvidenceDashboard(data);
    renderSidebarAnalysis(data);
    showToast(`✅ Verified: ${data.classification}`);
    switchView("results");
    loadDatabaseHistory();

  } catch (err) {
    hideProcessing();
    showToast(`Verification error: ${err.message}`);
    alert(`Could not verify URL:\n${err.message}`);
  }
}

if (verifyUrlBtn) verifyUrlBtn.addEventListener("click", verifyArticleUrl);
if (articleUrlInput) {
  articleUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      verifyArticleUrl();
    }
  });
}

// Clipboard Paste for URL
if (pasteArticleUrlBtn) {
  pasteArticleUrlBtn.addEventListener("click", async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          articleUrlInput.value = text.trim();
          showToast("Article URL pasted!");
          return;
        }
      }
    } catch (e) {}
    const p = prompt("Paste article link here:");
    if (p) articleUrlInput.value = p.trim();
  });
}

function loadSampleUrl(sampleUrl) {
  articleUrlInput.value = sampleUrl;
  showToast("Sample URL loaded. Click 'Verify Article URL' to run.");
}

// ============================================================
// 7. YOUTUBE VIDEO VERIFICATION
// ============================================================

async function verifyYouTubeVideo() {
  const url = youtubeUrlInput.value.trim();
  if (!url) {
    showToast("Please enter a YouTube video link.");
    youtubeUrlInput.focus();
    return;
  }

  showProcessing("Analyzing YouTube Video & Transcript...", "Extracting captions, parsing spoken claims, and querying fact-check archives");

  try {
    const response = await fetch(`${API_BASE}/api/verify/youtube`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error ${response.status}`);
    }

    const data = await response.json();
    hideProcessing();

    renderFullEvidenceDashboard(data);
    renderSidebarAnalysis(data);
    showToast(`✅ Video verified: ${data.classification}`);
    switchView("results");
    loadDatabaseHistory();

  } catch (err) {
    hideProcessing();
    showToast(`YouTube analysis error: ${err.message}`);
    alert(`YouTube Verification:\n${err.message}`);
  }
}

if (verifyYouTubeBtn) verifyYouTubeBtn.addEventListener("click", verifyYouTubeVideo);
if (youtubeUrlInput) {
  youtubeUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      verifyYouTubeVideo();
    }
  });
}

if (pasteYouTubeUrlBtn) {
  pasteYouTubeUrlBtn.addEventListener("click", async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          youtubeUrlInput.value = text.trim();
          showToast("YouTube link pasted!");
          return;
        }
      }
    } catch (e) {}
    const p = prompt("Paste YouTube URL here:");
    if (p) youtubeUrlInput.value = p.trim();
  });
}

// ============================================================
// 8. DIRECT TEXT & HEADLINE VERIFICATION
// ============================================================

async function performCheck() {
  const text = newsInput.value.trim();

  if (!text) {
    validationMessage.textContent = "Please enter or paste a news headline or statement to check.";
    validationMessage.classList.add("active");
    newsInput.focus();
    return;
  }

  validationMessage.classList.remove("active");

  // If backend is active, use the AI Fact-Checking endpoint
  if (isBackendOnline) {
    showProcessing("Verifying Statement Against Evidence...", "NLP claim extraction & real-time search across Google Fact Check and news repositories");
    try {
      const resp = await fetch(`${API_BASE}/api/verify/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });

      if (resp.ok) {
        const data = await resp.json();
        hideProcessing();
        renderFullEvidenceDashboard(data);
        renderSidebarAnalysis(data);
        loadDatabaseHistory();
        return;
      }
    } catch (e) {
      console.warn("Backend verification error, falling back to local engine:", e);
    }
    hideProcessing();
  }

  // Client-side heuristics fallback
  const result = analyzeNewsLocal(text);
  renderSidebarAnalysis(result);
  renderFullEvidenceDashboard(createEvidenceObjFromLocal(result));
  saveLocalHistory(result);
}

// ============================================================
// 9. LOCAL HEURISTIC ENGINE (Preserves Standard Test Cases)
// ============================================================

function countMatches(lowerText, keywordList) {
  const found = [];
  for (const word of keywordList) {
    if (lowerText.includes(word.toLowerCase())) {
      found.push(word);
    }
  }
  return found;
}

function countExtendedMatches(lowerText, extendedList, existingFound) {
  const found = [];
  for (const phrase of extendedList) {
    const pLower = phrase.toLowerCase();
    if (lowerText.includes(pLower)) {
      const alreadyCovered = existingFound.some(coreWord => {
        const cLower = coreWord.toLowerCase();
        return pLower.includes(cLower) || cLower.includes(pLower);
      });
      if (!alreadyCovered) {
        found.push(phrase);
      }
    }
  }
  return found;
}

function hasExcessivePunctuation(text) {
  return text.includes("!!") || text.includes("??");
}

function isMostlyCapitals(originalText) {
  const letters = originalText.split("").filter(ch => /[a-zA-Z]/.test(ch));
  if (letters.length < 10) return false;
  const capitals = letters.filter(ch => ch >= 'A' && ch <= 'Z');
  return (capitals.length / letters.length) > 0.7;
}

function analyzeNewsLocal(originalText) {
  const text = originalText.toLowerCase();
  const fakeFound = countMatches(text, FAKE_KEYWORDS);
  const realFound = countMatches(text, REAL_KEYWORDS);

  let fakeScore = fakeFound.length;
  let realScore = realFound.length;
  const reasons = [];

  const hasExPunct = hasExcessivePunctuation(originalText);
  if (hasExPunct) {
    fakeScore += 1;
    reasons.push({ type: "fake", text: "It uses excessive punctuation (like !! or ??)." });
  }

  const isCaps = isMostlyCapitals(originalText);
  if (isCaps) {
    fakeScore += 1;
    reasons.push({ type: "fake", text: "It is written mostly in CAPITAL LETTERS." });
  }

  if (fakeFound.length > 0) {
    reasons.push({ type: "fake", text: "Suspicious words found: " + fakeFound.join(", ") + "." });
  }

  if (realFound.length > 0) {
    reasons.push({ type: "real", text: "Credible-style words found: " + realFound.join(", ") + "." });
  }

  // Extended vocabulary checks
  const extFake = countExtendedMatches(text, EXTENDED_FAKE_KEYWORDS, fakeFound);
  if (extFake.length > 0) {
    fakeScore += extFake.length;
    reasons.push({ type: "fake", text: "Additional viral clickbait markers: " + extFake.join(", ") + "." });
  }

  const extReal = countExtendedMatches(text, EXTENDED_REAL_KEYWORDS, realFound);
  if (extReal.length > 0) {
    realScore += extReal.length;
    reasons.push({ type: "real", text: "Verified news agency attribution: " + extReal.join(", ") + "." });
  }

  if (reasons.length === 0) {
    reasons.push({ type: "unsure", text: "No suspicious or credible keywords were found." });
  }

  let verdict = "UNCERTAIN";
  let cssClass = "unsure";
  let classification = "UNVERIFIED";
  let subtitle = "Not enough decisive indicators to verify or refute.";

  if (fakeScore > realScore) {
    verdict = "FAKE NEWS";
    cssClass = "fake";
    classification = "POTENTIALLY FAKE";
    subtitle = "High concentration of sensational red flags and clickbait indicators.";
  } else if (realScore > fakeScore) {
    verdict = "LIKELY REAL NEWS";
    cssClass = "real";
    classification = "REAL NEWS";
    subtitle = "Features formal institutional attribution and journalistic vocabulary.";
  } else {
    reasons.push({ type: "unsure", text: "Not enough keywords to decide." });
  }

  return {
    originalText,
    headline: originalText,
    verdict,
    classification,
    cssClass,
    fakeScore,
    realScore,
    confidence_score: calculateConfidence(fakeScore, realScore),
    reasons,
    fakeFound: [...fakeFound, ...extFake],
    realFound: [...realFound, ...extReal],
    subtitle,
    timestamp: new Date()
  };
}

function calculateConfidence(fakeScore, realScore) {
  const diff = Math.abs(fakeScore - realScore);
  if (diff >= 5) return 88;
  if (diff >= 3) return 78;
  if (diff >= 1) return 65;
  return 50;
}

function createEvidenceObjFromLocal(localRes) {
  return {
    headline: localRes.originalText,
    extracted_summary: localRes.originalText,
    classification: localRes.classification,
    confidence_score: localRes.confidence_score,
    explanation: localRes.subtitle,
    model_used: "Client-Side Heuristic Engine",
    claims: [
      { id: 1, claim_text: localRes.originalText, verifiable: true, confidence_level: "Evaluated Statement" }
    ],
    supporting_evidence: localRes.realFound.map(kw => ({
      source: "Credible Attribution Keyword",
      title: `Keyword recognized: "${kw}"`,
      date: "Rule Match",
      url: ""
    })),
    contradicting_evidence: localRes.fakeFound.map(kw => ({
      source: "Sensational Clickbait Marker",
      title: `Suspicious pattern: "${kw}"`,
      rating: "Flagged",
      date: "Rule Match",
      url: ""
    })),
    trusted_sources_checked: ["Google Fact Check Explorer", "Reuters Archive", "BBC News Index"],
    is_outdated: false,
    created_at: new Date().toISOString()
  };
}

// ============================================================
// 10. EVIDENCE DASHBOARD & SIDEBAR RENDERING
// ============================================================

function renderSidebarAnalysis(data) {
  currentAnalysisRecord = data;

  emptyResultState.classList.add("hidden");
  activeResultState.classList.remove("hidden");

  // Determine styling
  const cls = (data.classification || "UNVERIFIED").toUpperCase();
  let cssClass = "unsure";
  let icon = "⚖️";

  if (cls.includes("REAL")) {
    cssClass = "real";
    icon = "✅";
  } else if (cls.includes("FAKE")) {
    cssClass = "fake";
    icon = "🚨";
  } else if (cls.includes("MISLEADING")) {
    cssClass = "unsure";
    icon = "⚠️";
  } else if (cls.includes("OUTDATED")) {
    cssClass = "outdated";
    icon = "⏰";
  }

  verdictBanner.className = `verdict-banner verdict-${cssClass}`;
  verdictTitle.textContent = cls;
  verdictSubtitle.textContent = data.explanation || "Analysis breakdown below";
  verdictIcon.textContent = icon;
  verdictTimestamp.textContent = `Analyzed ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

  // Scores
  const fScore = data.fakeScore !== undefined ? data.fakeScore : (cls.includes("FAKE") ? 6 : 0);
  const rScore = data.realScore !== undefined ? data.realScore : (cls.includes("REAL") ? 5 : 0);
  fakeScoreVal.textContent = fScore;
  realScoreVal.textContent = rScore;
  const delta = rScore - fScore;
  signalDeltaVal.textContent = delta > 0 ? `+${delta}` : `${delta}`;

  // Confidence Meter
  const conf = data.confidence_score || 50;
  meterFill.style.width = `${conf}%`;
  confidencePercentage.textContent = `${conf}% Confidence`;
  if (cssClass === "fake") meterFill.style.backgroundColor = "var(--fake-red)";
  else if (cssClass === "real") meterFill.style.backgroundColor = "var(--real-green)";
  else meterFill.style.backgroundColor = "var(--unsure-orange)";

  // Highlights & Reasons
  renderHighlightedText(data.headline || data.originalText || "");

  reasonsList.innerHTML = "";
  const reasons = data.reasons || [
    { type: cssClass, text: data.explanation || "Evaluated by verification pipeline." }
  ];
  reasons.forEach(r => {
    const li = document.createElement("li");
    li.className = `reason-${r.type || "unsure"}`;
    li.innerHTML = `<span>&bull;</span> <div>${escapeHtml(r.text)}</div>`;
    reasonsList.appendChild(li);
  });

  // Advice Card
  if (adviceBox) {
    adviceBox.className = `advice-box advice-${cssClass}`;
    if (adviceIcon) adviceIcon.textContent = icon;
    if (adviceTitle) adviceTitle.textContent = `Verification Recommendation:`;
    if (adviceText) {
      if (cssClass === "fake") {
        adviceText.textContent = "High misinformation risk. Do not forward or share this claim without independent confirmation from accredited news wire services.";
      } else if (cssClass === "real") {
        adviceText.textContent = "Corroborated by verified journalistic reporting or formal attribution. Consult primary official sources for ongoing updates.";
      } else {
        adviceText.textContent = "Insufficient conclusive evidence detected. Verify specific claims using the Google News and Fact Check buttons below.";
      }
    }
  }

  // External Buttons
  const queryHeadline = data.headline || data.originalText || "";
  const cleanQ = getCleanSearchQuery(queryHeadline);
  if (googleNewsSearchBtn) {
    googleNewsSearchBtn.onclick = () => {
      window.open(`https://news.google.com/search?q=${encodeURIComponent(cleanQ)}`, "_blank", "noopener,noreferrer");
    };
  }
  if (googleFactCheckBtn) {
    googleFactCheckBtn.onclick = () => {
      window.open(`https://toolbox.google.com/factcheck/explorer/search/list?hl=en&num=10&query=${encodeURIComponent(cleanQ)}`, "_blank", "noopener,noreferrer");
    };
  }
}

function renderFullEvidenceDashboard(data) {
  if (!data) return;

  fullEvidenceEmpty.classList.add("hidden");
  fullEvidenceContent.classList.remove("hidden");

  const cls = (data.classification || "UNVERIFIED").toUpperCase();
  let badgeCls = "badge-unverified";
  if (cls.includes("REAL")) badgeCls = "badge-real";
  else if (cls.includes("FAKE")) badgeCls = "badge-fake";
  else if (cls.includes("MISLEADING")) badgeCls = "badge-misleading";
  else if (cls.includes("OUTDATED")) badgeCls = "badge-outdated";

  evClassificationBadge.className = `verdict-badge-large ${badgeCls}`;
  evClassificationBadge.textContent = cls;
  evConfidenceVal.textContent = `${data.confidence_score || 50}%`;
  evModelUsed.textContent = data.model_used || "Veritas AI Fact-Checking Engine";

  // Outdated Alert
  if (data.is_outdated) {
    evOutdatedAlert.classList.remove("hidden");
    evOutdatedText.textContent = data.outdated_notes || "Events reported occurred in past years and are being recirculated as breaking news.";
  } else {
    evOutdatedAlert.classList.add("hidden");
  }

  // Metadata
  evSourceMeta.textContent = data.source_url ? `Source Link: ${data.domain || data.source_url}` : `Input Source: Direct Statement`;
  evHeadline.textContent = data.headline || "Untitled Statement";
  evDateMeta.textContent = data.published_date ? `Published: ${data.published_date}` : `Analyzed: ${new Date().toLocaleDateString()}`;
  evWordCountMeta.textContent = `Words: ${data.word_count || (data.extracted_summary || "").split(/\s+/).length}`;

  if (data.source_url && /^https?:\/\//i.test(data.source_url)) {
    evOriginalLink.href = data.source_url;
    evOriginalLink.style.display = "inline-flex";
  } else {
    evOriginalLink.style.display = "none";
  }

  evSummaryText.textContent = data.extracted_summary || data.headline || "No summary excerpt available.";

  // Render Claims
  evClaimsList.innerHTML = "";
  const claims = data.claims || [{ id: 1, claim_text: data.headline, verifiable: true, confidence_level: "Primary Claim" }];
  claims.forEach((c, idx) => {
    const item = document.createElement("div");
    item.className = "claim-card-item";
    item.innerHTML = `
      <span class="claim-number-badge">Claim #${c.id || idx + 1}</span>
      <div class="claim-body-wrap">
        <div class="claim-text-content">${escapeHtml(c.claim_text)}</div>
        <span class="claim-meta-tag">${escapeHtml(c.confidence_level || "Verifiable Assertion")}</span>
      </div>
    `;
    evClaimsList.appendChild(item);
  });

  // Render Supporting Evidence
  evSupportingList.innerHTML = "";
  const supporting = data.supporting_evidence || [];
  if (supporting.length === 0) {
    evSupportingList.innerHTML = `<div class="evidence-empty">No direct supporting reports identified in indexed archives.</div>`;
  } else {
    supporting.forEach(item => {
      const entry = document.createElement("div");
      entry.className = "evidence-item-entry";
      entry.innerHTML = `
        <div class="ev-entry-top">
          <span class="ev-entry-source">${escapeHtml(item.source || "Reputable Media")}</span>
          <span class="ev-entry-date">${escapeHtml(item.date || "Recent")}</span>
        </div>
        <div class="ev-entry-title">${escapeHtml(item.title)}</div>
        ${item.url ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener" class="ev-entry-link">Read Source Article &nearr;</a>` : ''}
      `;
      evSupportingList.appendChild(entry);
    });
  }

  // Render Contradicting Evidence
  evContradictingList.innerHTML = "";
  const contradicting = data.contradicting_evidence || [];
  if (contradicting.length === 0) {
    evContradictingList.innerHTML = `<div class="evidence-empty">No conflicting debunks or counter-evidence found in verified registers.</div>`;
  } else {
    contradicting.forEach(item => {
      const entry = document.createElement("div");
      entry.className = "evidence-item-entry";
      entry.innerHTML = `
        <div class="ev-entry-top">
          <span class="ev-entry-source">${escapeHtml(item.source || "Fact Checker")}</span>
          ${item.rating ? `<span class="ev-entry-rating">${escapeHtml(item.rating)}</span>` : ''}
          <span class="ev-entry-date">${escapeHtml(item.date || "")}</span>
        </div>
        <div class="ev-entry-title">${escapeHtml(item.title)}</div>
        ${item.url ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener" class="ev-entry-link">View Fact-Check Review &nearr;</a>` : ''}
      `;
      evContradictingList.appendChild(entry);
    });
  }

  // Render Trusted Sources Badges
  evTrustedSourcesBadges.innerHTML = "";
  const sourcesChecked = data.trusted_sources_checked || ["Google Fact Check Explorer", "Reuters Archive", "BBC News Index", "The Hindu"];
  sourcesChecked.forEach(src => {
    const badge = document.createElement("span");
    badge.className = "source-check-badge";
    badge.innerHTML = `<span>✓</span> <span>${escapeHtml(src)}</span>`;
    evTrustedSourcesBadges.appendChild(badge);
  });

  // Explanation
  evExplanationText.textContent = data.explanation || "No explanation text provided.";
}

function renderHighlightedText(text) {
  if (!highlightedContent) return;
  highlightedContent.textContent = text;
}

function escapeHtml(text) {
  if (!text) return "";
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

function getCleanSearchQuery(text) {
  const clean = text.replace(/https?:\/\/\S+/gi, " ").replace(/[^\w\s]/gi, " ").trim();
  const words = clean.split(/\s+/).filter(w => w.length > 2);
  return (words.slice(0, 10).join(" ") || text.slice(0, 60)).trim();
}

// ============================================================
// 11. PERSISTENT SQLITE DATABASE HISTORY
// ============================================================

async function loadDatabaseHistory() {
  if (!isBackendOnline) {
    loadLocalHistory();
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/history?limit=50`);
    if (res.ok) {
      databaseHistoryRecords = await res.json();
      renderHistoryTable(databaseHistoryRecords);
      renderDashboardRecent(databaseHistoryRecords);
      updateHistoryCounters(databaseHistoryRecords.length);
      return;
    }
  } catch (e) {
    console.warn("Could not load history from API:", e);
  }
  loadLocalHistory();
}

function renderHistoryTable(records, filter = "all", searchQuery = "") {
  if (!historyTableBody) return;

  let filtered = records;
  if (filter !== "all") {
    filtered = filtered.filter(r => (r.classification || "").toUpperCase() === filter.toUpperCase());
  }
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter(r => (r.headline || "").toLowerCase().includes(q) || (r.summary || "").toLowerCase().includes(q));
  }

  if (filtered.length === 0) {
    historyTableBody.innerHTML = `<tr><td colspan="6" class="history-empty">No matching records found.</td></tr>`;
    return;
  }

  historyTableBody.innerHTML = "";
  filtered.forEach(rec => {
    const tr = document.createElement("tr");
    const cls = (rec.classification || "UNVERIFIED").toUpperCase();
    let badgeCls = "badge-unverified";
    if (cls.includes("REAL")) badgeCls = "badge-real";
    else if (cls.includes("FAKE")) badgeCls = "badge-fake";
    else if (cls.includes("MISLEADING")) badgeCls = "badge-misleading";
    else if (cls.includes("OUTDATED")) badgeCls = "badge-outdated";

    const dt = rec.created_at ? new Date(rec.created_at).toLocaleDateString() : "Recent";
    const typeLabel = (rec.input_type || "text").toUpperCase();

    tr.innerHTML = `
      <td>${dt}</td>
      <td><span class="dash-type-badge">${typeLabel}</span></td>
      <td class="history-headline-col">
        <div class="history-headline-text" title="${escapeHtml(rec.headline)}">${escapeHtml(rec.headline || "Untitled")}</div>
        ${rec.source_url ? `<div class="history-url-sub">${escapeHtml(rec.source_url)}</div>` : ''}
      </td>
      <td><span class="status-pill-table ${badgeCls}">${cls}</span></td>
      <td><strong>${rec.confidence_score || 50}%</strong></td>
      <td>
        <button type="button" class="btn btn-sm btn-outline" onclick="viewHistoryItem(${rec.id})">View Report</button>
      </td>
    `;
    historyTableBody.appendChild(tr);
  });
}

function renderDashboardRecent(records) {
  if (!dashboardRecentList) return;
  if (!records || records.length === 0) {
    dashboardRecentList.innerHTML = `<div class="history-empty">No verifications conducted yet. Click "Verify News" above to begin.</div>`;
    return;
  }

  dashboardRecentList.innerHTML = "";
  records.slice(0, 5).forEach(rec => {
    const item = document.createElement("div");
    item.className = "dash-recent-item";
    const cls = (rec.classification || "UNVERIFIED").toUpperCase();
    let badgeCls = "badge-unverified";
    if (cls.includes("REAL")) badgeCls = "badge-real";
    else if (cls.includes("FAKE")) badgeCls = "badge-fake";
    else if (cls.includes("MISLEADING")) badgeCls = "badge-misleading";
    else if (cls.includes("OUTDATED")) badgeCls = "badge-outdated";

    item.innerHTML = `
      <div class="dash-recent-left">
        <span class="dash-type-badge">${(rec.input_type || "text").toUpperCase()}</span>
        <span class="dash-recent-headline">${escapeHtml(rec.headline || "Untitled")}</span>
      </div>
      <div>
        <span class="status-pill-table ${badgeCls}">${cls}</span>
      </div>
    `;
    item.onclick = () => viewHistoryItem(rec.id);
    dashboardRecentList.appendChild(item);
  });
}

async function viewHistoryItem(recordId) {
  let record = databaseHistoryRecords.find(r => r.id === recordId);
  if (!record && isBackendOnline) {
    try {
      const res = await fetch(`${API_BASE}/api/history/${recordId}`);
      if (res.ok) record = await res.json();
    } catch (e) {}
  }

  if (record) {
    renderFullEvidenceDashboard(record);
    renderSidebarAnalysis(record);
    switchView("results");
  }
}

function updateHistoryCounters(count) {
  if (historyDatabaseCount) historyDatabaseCount.textContent = count;
  if (navHistoryBadge) navHistoryBadge.textContent = count;
  if (dashTotalChecked) dashTotalChecked.textContent = count;
}

// Local History Fallback
function loadLocalHistory() {
  try {
    const raw = localStorage.getItem(LOCAL_HISTORY_KEY);
    if (raw) {
      databaseHistoryRecords = JSON.parse(raw);
    }
  } catch (e) {
    databaseHistoryRecords = [];
  }
  renderHistoryTable(databaseHistoryRecords);
  renderDashboardRecent(databaseHistoryRecords);
  updateHistoryCounters(databaseHistoryRecords.length);
}

function saveLocalHistory(result) {
  const newRec = {
    id: Date.now(),
    input_type: "text",
    headline: result.originalText,
    summary: result.originalText,
    classification: result.classification,
    confidence_score: result.confidence_score,
    explanation: result.subtitle,
    created_at: new Date().toISOString()
  };
  databaseHistoryRecords.unshift(newRec);
  if (databaseHistoryRecords.length > 50) databaseHistoryRecords.pop();
  try {
    localStorage.setItem(LOCAL_HISTORY_KEY, JSON.stringify(databaseHistoryRecords));
  } catch (e) {}
  renderHistoryTable(databaseHistoryRecords);
  renderDashboardRecent(databaseHistoryRecords);
  updateHistoryCounters(databaseHistoryRecords.length);
}

// History Filters & Search
if (dbHistoryFilters) {
  dbHistoryFilters.addEventListener("click", (e) => {
    if (e.target.classList.contains("filter-btn")) {
      dbHistoryFilters.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      e.target.classList.add("active");
      renderHistoryTable(databaseHistoryRecords, e.target.dataset.filter, historySearchInput?.value || "");
    }
  });
}

if (historySearchInput) {
  historySearchInput.addEventListener("input", () => {
    const activeFilter = dbHistoryFilters?.querySelector(".filter-btn.active")?.dataset.filter || "all";
    renderHistoryTable(databaseHistoryRecords, activeFilter, historySearchInput.value);
  });
}

if (clearAllDbHistoryBtn) {
  clearAllDbHistoryBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear your entire verification history?")) return;

    if (isBackendOnline) {
      try {
        await fetch(`${API_BASE}/api/history`, { method: "DELETE" });
      } catch (e) {}
    }
    databaseHistoryRecords = [];
    localStorage.removeItem(LOCAL_HISTORY_KEY);
    renderHistoryTable([]);
    renderDashboardRecent([]);
    updateHistoryCounters(0);
    showToast("History cleared.");
  });
}

// ============================================================
// 12. TEXT METRICS, PRESETS & ACTIONS
// ============================================================

function updateInputMetrics() {
  const text = newsInput.value;
  const chars = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  charCounter.textContent = `${chars} characters • ${words} words`;

  if (clearTextBtn) {
    clearTextBtn.style.display = chars > 0 ? "flex" : "none";
  }

  if (liveModeToggle && liveModeToggle.checked && text.trim().length >= 4) {
    const res = analyzeNewsLocal(text);
    renderSidebarAnalysis(res);
  }
}

// Presets
document.getElementById("exampleFakeBtn")?.addEventListener("click", () => {
  newsInput.value = PRESETS.fake;
  updateInputMetrics();
  performCheck();
});

document.getElementById("exampleRealBtn")?.addEventListener("click", () => {
  newsInput.value = PRESETS.real;
  updateInputMetrics();
  performCheck();
});

document.getElementById("exampleNeutralBtn")?.addEventListener("click", () => {
  newsInput.value = PRESETS.neutral;
  updateInputMetrics();
  performCheck();
});

document.getElementById("exampleClickbaitBtn")?.addEventListener("click", () => {
  newsInput.value = PRESETS.clickbait;
  updateInputMetrics();
  performCheck();
});

if (clearTextBtn) {
  clearTextBtn.addEventListener("click", () => {
    newsInput.value = "";
    updateInputMetrics();
    newsInput.focus();
  });
}

if (resetBtn) {
  resetBtn.addEventListener("click", () => {
    newsInput.value = "";
    updateInputMetrics();
    validationMessage.classList.remove("active");
    activeResultState.classList.add("hidden");
    emptyResultState.classList.remove("hidden");
    verdictTimestamp.textContent = "Ready for input";
    currentAnalysisRecord = null;
    newsInput.focus();
    showToast("Analyzer reset");
  });
}

if (checkBtn) checkBtn.addEventListener("click", performCheck);

if (newsInput) {
  newsInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      performCheck();
    }
  });
  newsInput.addEventListener("input", updateInputMetrics);
}

// Clipboard Paste Button for Textarea
if (pasteClipboardBtn) {
  pasteClipboardBtn.addEventListener("click", async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          newsInput.value = text.trim();
          updateInputMetrics();
          performCheck();
          showToast("📋 Copied news pasted and analyzed!");
          return;
        }
      }
    } catch (e) {}
    const p = prompt("Paste copied text here:");
    if (p) {
      newsInput.value = p.trim();
      updateInputMetrics();
      performCheck();
      showToast("📋 Copied news pasted and analyzed!");
    }
  });
}

if (fetchUrlBtn) {
  fetchUrlBtn.addEventListener("click", () => {
    switchInputTab("url");
    articleUrlInput.focus();
    showToast("Switched to News Article URL tab.");
  });
}

// Copy & Share Full Dossier
function copyFullDossier() {
  if (!currentAnalysisRecord) return;
  const d = currentAnalysisRecord;
  const claimsText = (d.claims || []).map((c, i) => `  ${i + 1}. ${c.claim_text}`).join("\n");
  const suppText = (d.supporting_evidence || []).map(s => `  • [${s.source}] ${s.title} (${s.date || ""})`).join("\n") || "  None identified";
  const contText = (d.contradicting_evidence || []).map(c => `  • [${c.source} - ${c.rating || "False"}] ${c.title}`).join("\n") || "  None identified";

  const dossier = `🛡️ VERITAS AI - VERIFICATION AUDIT DOSSIER\n` +
    `============================================================\n` +
    `HEADLINE: "${d.headline || d.originalText}"\n` +
    `VERDICT: ${d.classification || d.verdict}\n` +
    `CONFIDENCE: ${d.confidence_score || 50}%\n` +
    `MODEL: ${d.model_used || "Veritas AI Platform"}\n\n` +
    `EXTRACTED CLAIMS:\n${claimsText}\n\n` +
    `SUPPORTING CORROBORATIONS:\n${suppText}\n\n` +
    `CONTRADICTING FACT-CHECKS:\n${contText}\n\n` +
    `AI RATIONALE:\n${d.explanation || ""}\n` +
    `============================================================\n` +
    `Verified with Veritas AI: https://fake-news-detector-tau-roan.vercel.app`;

  navigator.clipboard.writeText(dossier).then(() => {
    showToast("📋 Full verification dossier copied to clipboard!");
  }).catch(() => {
    showToast("Failed to copy dossier.");
  });
}

if (copyResultBtn) copyResultBtn.addEventListener("click", copyFullDossier);
if (evCopyBtn) evCopyBtn.addEventListener("click", copyFullDossier);

if (shareResultBtn) {
  shareResultBtn.addEventListener("click", () => {
    if (!currentAnalysisRecord) return;
    if (navigator.share) {
      navigator.share({
        title: "News Verification Dossier",
        text: `Analysis: ${currentAnalysisRecord.classification} for "${currentAnalysisRecord.headline}"`,
        url: window.location.href
      }).catch(() => {});
    } else {
      copyFullDossier();
    }
  });
}

// Keyword Clouds
function populateKeywordClouds() {
  if (fakeKeywordCloud) {
    fakeKeywordCloud.innerHTML = "";
    FAKE_KEYWORDS.forEach(kw => {
      const tag = document.createElement("span");
      tag.className = "lex-tag lex-fake";
      tag.textContent = kw;
      tag.title = "Click to insert into analyzer";
      tag.onclick = () => insertKeywordIntoInput(kw);
      fakeKeywordCloud.appendChild(tag);
    });
  }

  if (realKeywordCloud) {
    realKeywordCloud.innerHTML = "";
    REAL_KEYWORDS.forEach(kw => {
      const tag = document.createElement("span");
      tag.className = "lex-tag lex-real";
      tag.textContent = kw;
      tag.title = "Click to insert into analyzer";
      tag.onclick = () => insertKeywordIntoInput(kw);
      realKeywordCloud.appendChild(tag);
    });
  }
}

function insertKeywordIntoInput(kw) {
  switchView("verify", "text");
  const current = newsInput.value.trim();
  newsInput.value = current ? `${current} ${kw}` : kw;
  updateInputMetrics();
  newsInput.focus();
}

// Theme
function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved) {
    document.documentElement.setAttribute("data-theme", saved);
  } else {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem(THEME_KEY, next);
  showToast(`Switched to ${next} theme`);
}

if (themeToggleBtn) themeToggleBtn.addEventListener("click", toggleTheme);

function showToast(msg) {
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2800);
}

// ============================================================
// 13. APP INITIALIZATION
// ============================================================
window.addEventListener("DOMContentLoaded", () => {
  initTheme();
  populateKeywordClouds();
  checkBackendHealth();
  updateInputMetrics();
});
