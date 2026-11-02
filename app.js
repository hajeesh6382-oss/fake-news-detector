/**
 * FAKE NEWS DETECTOR - FRONTEND ENGINE & LINGUISTIC HEURISTICS
 * Faithfully mirrors the Python rule engine with client-side interactive enhancements,
 * external web news import/paste tools, domain reputation checks, and external fact checking.
 */

// ============================================================
// KEYWORD DICTIONARIES (Core Python Prototype)
// ============================================================
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

// Extended keywords for deeper analysis of web-copied news articles
const EXTENDED_FAKE_KEYWORDS = [
  "miracle cure", "share before deleted", "share before banned",
  "forward this to everyone", "100% genuine", "government won't tell you",
  "secret remedy", "urgent alert", "classified leaked", "wake up people",
  "mind blowing", "they are lying to you", "click here immediately",
  "act fast before", "hidden truth exposed", "deep state", "forwarded as received",
  "cure for cancer in 24 hours"
];

const EXTENDED_REAL_KEYWORDS = [
  "reuters", "associated press", "bbc news", "cnn", "ndtv", "the hindu",
  "the guardian", "new york times", "washington post", "bloomberg",
  "world health organization", "press release", "official spokesperson",
  "peer-reviewed", "clinical trial", "supreme court", "high court",
  "ministry of external affairs", "pib fact check", "investigation revealed",
  "corroborated by sources"
];

// High-credibility news domains and institutions
const TRUSTED_DOMAINS = [
  "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com", "thehindu.com",
  "ndtv.com", "indiatoday.in", "indianexpress.com", "hindustantimes.com",
  "nytimes.com", "washingtonpost.com", "theguardian.com", "bloomberg.com",
  "who.int", "pib.gov.in", "gov.in", "cdc.gov", "nih.gov", "un.org"
];

// Suspicious domains / TLDs often seen in fake news forwards
const SUSPICIOUS_DOMAIN_PATTERNS = [
  ".xyz", ".top", ".buzz", ".click", ".free", ".tk", ".ml", ".ga", ".cf"
];

// Presets for quick evaluation (retains standard test cases)
const PRESETS = {
  fake: "SHOCKING!! Miracle cure exposed, share before it is banned",
  real: "According to the Ministry of Health, an official report was published today",
  neutral: "The weather is nice today",
  clickbait: "URGENT!! Free money guaranteed, doctors hate this 100% cure, share before it gets banned!!"
};

// State
let historyState = [];
const STORAGE_KEY = "veritas_analysis_history";
const THEME_KEY = "veritas_theme_preference";

// DOM References
const newsInput = document.getElementById("newsInput");
const checkBtn = document.getElementById("checkBtn");
const resetBtn = document.getElementById("resetBtn");
const clearTextBtn = document.getElementById("clearTextBtn");
const charCounter = document.getElementById("charCounter");
const validationMessage = document.getElementById("validationMessage");
const liveModeToggle = document.getElementById("liveModeToggle");
const themeToggleBtn = document.getElementById("themeToggleBtn");
const toast = document.getElementById("toast");

// Web News Helper Toolbar
const pasteClipboardBtn = document.getElementById("pasteClipboardBtn");
const fetchUrlBtn = document.getElementById("fetchUrlBtn");

// Result DOM elements
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
const copyResultBtn = document.getElementById("copyResultBtn");
const shareResultBtn = document.getElementById("shareResultBtn");

// Clear Analysis Advice Box & Fact Check Buttons
const adviceBox = document.getElementById("adviceBox");
const adviceIcon = document.getElementById("adviceIcon");
const adviceTitle = document.getElementById("adviceTitle");
const adviceText = document.getElementById("adviceText");
const googleNewsSearchBtn = document.getElementById("googleNewsSearchBtn");
const googleFactCheckBtn = document.getElementById("googleFactCheckBtn");

// History DOM elements
const historyList = document.getElementById("historyList");
const historyCount = document.getElementById("historyCount");
const clearHistoryBtn = document.getElementById("clearHistoryBtn");
const historyFilters = document.getElementById("historyFilters");

// Lexicon tag containers
const fakeKeywordCloud = document.getElementById("fakeKeywordCloud");
const realKeywordCloud = document.getElementById("realKeywordCloud");

// Current analysis reference
let currentAnalysis = null;

// ============================================================
// DETECTION ALGORITHM
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
      // Avoid double-counting if already captured by core words
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

function detectDomainReputation(text) {
  const lower = text.toLowerCase();
  for (const domain of TRUSTED_DOMAINS) {
    if (lower.includes(domain)) {
      return { type: "trusted", domain };
    }
  }
  for (const pattern of SUSPICIOUS_DOMAIN_PATTERNS) {
    if (lower.includes(pattern)) {
      return { type: "suspicious", pattern };
    }
  }
  return null;
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

function analyzeNews(originalText) {
  const text = originalText.toLowerCase();
  
  // 1. Core keyword matching (strictly preserves standard baseline scores)
  const fakeFound = countMatches(text, FAKE_KEYWORDS);
  const realFound = countMatches(text, REAL_KEYWORDS);
  
  let fakeScore = fakeFound.length;
  let realScore = realFound.length;
  const reasons = [];

  // 2. Style heuristics
  const hasExPunct = hasExcessivePunctuation(originalText);
  if (hasExPunct) {
    fakeScore += 1;
    reasons.push({
      type: "fake",
      text: "It uses excessive punctuation (like !! or ??)."
    });
  }

  const isCaps = isMostlyCapitals(originalText);
  if (isCaps) {
    fakeScore += 1;
    reasons.push({
      type: "fake",
      text: "It is written mostly in CAPITAL LETTERS."
    });
  }

  if (fakeFound.length > 0) {
    reasons.push({
      type: "fake",
      text: "Suspicious words found: " + fakeFound.join(", ") + "."
    });
  }

  if (realFound.length > 0) {
    reasons.push({
      type: "real",
      text: "Credible-style words found: " + realFound.join(", ") + "."
    });
  }

  // 3. Extended heuristics for web-copied news articles and forwards
  const extendedFakeFound = countExtendedMatches(text, EXTENDED_FAKE_KEYWORDS, fakeFound);
  if (extendedFakeFound.length > 0) {
    fakeScore += extendedFakeFound.length;
    reasons.push({
      type: "fake",
      text: "Additional clickbait / viral markers identified: " + extendedFakeFound.join(", ") + "."
    });
  }

  const extendedRealFound = countExtendedMatches(text, EXTENDED_REAL_KEYWORDS, realFound);
  if (extendedRealFound.length > 0) {
    realScore += extendedRealFound.length;
    reasons.push({
      type: "real",
      text: "Recognized authoritative news agency / verification attribution: " + extendedRealFound.join(", ") + "."
    });
  }

  // 4. Web domain reputation analysis
  const domainRep = detectDomainReputation(originalText);
  if (domainRep) {
    if (domainRep.type === "trusted") {
      realScore += 2;
      reasons.push({
        type: "real",
        text: "Source attribution from trusted high-reputation domain / institution: " + domainRep.domain + "."
      });
    } else if (domainRep.type === "suspicious") {
      fakeScore += 2;
      reasons.push({
        type: "fake",
        text: "Potentially suspicious or unverified web domain pattern detected: " + domainRep.pattern + "."
      });
    }
  }

  // Handle neutral or empty signals
  if (reasons.length === 0) {
    reasons.push({
      type: "unsure",
      text: "No suspicious or credible keywords were found."
    });
  }

  // Verdict decision
  let verdict = "UNCERTAIN";
  let cssClass = "unsure";
  let subtitle = "Not enough decisive indicators to verify or refute.";

  if (fakeScore > realScore) {
    verdict = "FAKE NEWS";
    cssClass = "fake";
    subtitle = "High concentration of sensational red flags and clickbait indicators.";
  } else if (realScore > fakeScore) {
    verdict = "LIKELY REAL NEWS";
    cssClass = "real";
    subtitle = "Features formal institutional attribution and journalistic vocabulary.";
  } else {
    reasons.push({
      type: "unsure",
      text: "Not enough keywords to decide."
    });
  }

  return {
    originalText,
    verdict,
    cssClass,
    fakeScore,
    realScore,
    reasons,
    fakeFound: [...fakeFound, ...extendedFakeFound],
    realFound: [...realFound, ...extendedRealFound],
    subtitle,
    timestamp: new Date()
  };
}

// Generate lucid advice for users based on evaluation
function generateAdvice(result) {
  if (result.cssClass === "fake") {
    return {
      icon: "🚨",
      title: "Misinformation Alert & Recommendations",
      text: "This news statement contains multiple hallmarks of viral disinformation, unverified clickbait, or artificial urgency markers. Authentic news reporting avoids emotional pressure and excessive sensationalism. We strongly recommend that you do not share or forward this text. Verify the claims using the Google News and Google Fact Check search buttons below."
    };
  } else if (result.cssClass === "real") {
    return {
      icon: "✅",
      title: "Credible Journalistic Attribution",
      text: "This statement contains formal attribution, institutional references, or recognized news agency vocabulary typical of credible reporting. While the linguistic framing is characteristic of legitimate media, always cross-reference critical claims directly with the primary institutional source or official press release."
    };
  } else {
    return {
      icon: "⚖️",
      title: "Neutral / Inconclusive Text",
      text: "This text lacks decisive linguistic indicators of either sensationalist clickbait or authoritative journalistic attribution. For an accurate assessment of web news, paste the complete headline, include the publication URL, or search the claim directly using the Google Fact Check tool below."
    };
  }
}

// Helper to sanitize search query for Google News / Fact Check
function getSearchQuery(text) {
  const clean = text.replace(/https?:\/\/\S+/gi, " ").replace(/[^\w\s]/gi, " ").trim();
  const words = clean.split(/\s+/).filter(w => w.length > 2);
  return (words.slice(0, 10).join(" ") || text.slice(0, 60)).trim();
}

// ============================================================
// UI RENDERING & HIGHLIGHTING
// ============================================================

function renderAnalysis(result) {
  currentAnalysis = result;

  // Switch empty state to active
  emptyResultState.classList.add("hidden");
  activeResultState.classList.remove("hidden");

  // Verdict Banner
  verdictBanner.className = `verdict-banner verdict-${result.cssClass}`;
  verdictTitle.textContent = result.verdict;
  verdictSubtitle.textContent = result.subtitle;

  if (result.cssClass === "fake") {
    verdictIcon.textContent = "🚨";
  } else if (result.cssClass === "real") {
    verdictIcon.textContent = "✅";
  } else {
    verdictIcon.textContent = "⚖️";
  }

  // Timestamp
  verdictTimestamp.textContent = `Analyzed ${result.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;

  // Scores
  fakeScoreVal.textContent = result.fakeScore;
  realScoreVal.textContent = result.realScore;
  const delta = result.realScore - result.fakeScore;
  signalDeltaVal.textContent = (delta > 0 ? `+${delta}` : `${delta}`);

  // Meter gauge calculation
  const total = result.fakeScore + result.realScore;
  let percentReal = 50;
  if (total > 0) {
    percentReal = Math.round((result.realScore / total) * 100);
  }

  meterFill.style.width = `${percentReal}%`;
  if (result.cssClass === "fake") {
    meterFill.style.backgroundColor = "var(--fake-red)";
    confidencePercentage.textContent = `${100 - percentReal}% Suspicious`;
  } else if (result.cssClass === "real") {
    meterFill.style.backgroundColor = "var(--real-green)";
    confidencePercentage.textContent = `${percentReal}% Credible`;
  } else {
    meterFill.style.backgroundColor = "var(--unsure-orange)";
    confidencePercentage.textContent = "50% Neutral / Inconclusive";
  }

  // Highlights
  renderHighlightedText(result);

  // Reasons list
  reasonsList.innerHTML = "";
  result.reasons.forEach(r => {
    const li = document.createElement("li");
    li.className = `reason-${r.type}`;
    li.innerHTML = `<span>&bull;</span> <div>${escapeHtml(r.text)}</div>`;
    reasonsList.appendChild(li);
  });

  // Clear Analysis Summary & Advice Card
  if (adviceBox && adviceTitle && adviceText) {
    const advice = generateAdvice(result);
    adviceBox.className = `advice-box advice-${result.cssClass}`;
    if (adviceIcon) adviceIcon.textContent = advice.icon;
    adviceTitle.textContent = advice.title;
    adviceText.textContent = advice.text;
  }

  // Configure external verification buttons
  const cleanQuery = getSearchQuery(result.originalText);
  if (googleNewsSearchBtn) {
    googleNewsSearchBtn.onclick = () => {
      window.open(`https://news.google.com/search?q=${encodeURIComponent(cleanQuery)}`, "_blank", "noopener,noreferrer");
    };
  }
  if (googleFactCheckBtn) {
    googleFactCheckBtn.onclick = () => {
      window.open(`https://toolbox.google.com/factcheck/explorer/search/list?hl=en&num=10&query=${encodeURIComponent(cleanQuery)}`, "_blank", "noopener,noreferrer");
    };
  }
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

function renderHighlightedText(result) {
  const text = result.originalText;
  const highlights = [];

  // Match fake keywords
  result.fakeFound.forEach(kw => {
    const regex = new RegExp(`(${escapeRegExp(kw)})`, "gi");
    let match;
    while ((match = regex.exec(text)) !== null) {
      highlights.push({
        start: match.index,
        end: match.index + match[0].length,
        cls: "kw-fake",
        word: match[0]
      });
    }
  });

  // Match real keywords
  result.realFound.forEach(kw => {
    const regex = new RegExp(`(${escapeRegExp(kw)})`, "gi");
    let match;
    while ((match = regex.exec(text)) !== null) {
      highlights.push({
        start: match.index,
        end: match.index + match[0].length,
        cls: "kw-real",
        word: match[0]
      });
    }
  });

  if (highlights.length === 0) {
    highlightedContent.textContent = text;
    return;
  }

  // Sort by start index
  highlights.sort((a, b) => a.start - b.start);

  // Filter overlapping highlights
  const merged = [];
  let lastEnd = 0;
  for (const h of highlights) {
    if (h.start >= lastEnd) {
      merged.push(h);
      lastEnd = h.end;
    }
  }

  // Build HTML fragments
  let html = "";
  let cursor = 0;
  for (const h of merged) {
    if (h.start > cursor) {
      html += escapeHtml(text.slice(cursor, h.start));
    }
    html += `<span class="kw-flag ${h.cls}">${escapeHtml(text.slice(h.start, h.end))}</span>`;
    cursor = h.end;
  }
  if (cursor < text.length) {
    html += escapeHtml(text.slice(cursor));
  }

  highlightedContent.innerHTML = html;
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ============================================================
// HISTORY MANAGER
// ============================================================

function loadHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      historyState = JSON.parse(raw);
    }
  } catch (e) {
    console.warn("Could not load history from storage", e);
    historyState = [];
  }
  renderHistory();
}

function saveHistory() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(historyState));
  } catch (e) {
    console.warn("Could not save history to storage", e);
  }
}

function addToHistory(result) {
  if (historyState.length > 0 && historyState[0].text === result.originalText) {
    return;
  }
  historyState.unshift({
    text: result.originalText,
    verdict: result.verdict,
    cssClass: result.cssClass,
    fakeScore: result.fakeScore,
    realScore: result.realScore,
    time: result.timestamp.toISOString()
  });

  if (historyState.length > 50) {
    historyState.pop();
  }
  saveHistory();
  renderHistory();
}

function renderHistory(filter = "all") {
  historyCount.textContent = historyState.length;

  if (historyState.length === 0) {
    historyList.innerHTML = `<li class="history-empty">No statements analyzed yet in this session.</li>`;
    return;
  }

  const filtered = historyState.filter(item => {
    if (filter === "all") return true;
    return item.cssClass === filter;
  });

  if (filtered.length === 0) {
    historyList.innerHTML = `<li class="history-empty">No items matching "${filter}".</li>`;
    return;
  }

  historyList.innerHTML = "";
  filtered.forEach(item => {
    const li = document.createElement("li");
    li.className = "history-item";
    li.title = "Click to reload this statement into analyzer";
    li.innerHTML = `
      <span class="history-item-text">${escapeHtml(item.text)}</span>
      <span class="history-tag tag-${item.cssClass}">${item.verdict}</span>
    `;

    li.addEventListener("click", () => {
      newsInput.value = item.text;
      updateInputMetrics();
      performCheck();
      newsInput.scrollIntoView({ behavior: "smooth", block: "center" });
    });

    historyList.appendChild(li);
  });
}

// ============================================================
// CORE CONTROLLER
// ============================================================

function performCheck() {
  const text = newsInput.value.trim();

  if (!text) {
    validationMessage.textContent = "Please enter or paste a news headline or statement to check.";
    validationMessage.classList.add("active");
    newsInput.focus();
    return;
  }

  validationMessage.classList.remove("active");
  const result = analyzeNews(text);
  renderAnalysis(result);
  addToHistory(result);
}

function updateInputMetrics() {
  const text = newsInput.value;
  const chars = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  charCounter.textContent = `${chars} characters • ${words} words`;

  if (chars > 0) {
    clearTextBtn.style.display = "flex";
  } else {
    clearTextBtn.style.display = "none";
  }

  if (liveModeToggle.checked && text.trim().length >= 4) {
    const result = analyzeNews(text);
    renderAnalysis(result);
  }
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 2500);
}

// ============================================================
// KEYWORD CLOUD INITIALIZATION
// ============================================================

function populateKeywordClouds() {
  FAKE_KEYWORDS.forEach(kw => {
    const tag = document.createElement("span");
    tag.className = "lex-tag lex-fake";
    tag.textContent = kw;
    tag.title = "Click to insert into analyzer";
    tag.addEventListener("click", () => {
      insertKeywordIntoInput(kw);
    });
    fakeKeywordCloud.appendChild(tag);
  });

  REAL_KEYWORDS.forEach(kw => {
    const tag = document.createElement("span");
    tag.className = "lex-tag lex-real";
    tag.textContent = kw;
    tag.title = "Click to insert into analyzer";
    tag.addEventListener("click", () => {
      insertKeywordIntoInput(kw);
    });
    realKeywordCloud.appendChild(tag);
  });
}

function insertKeywordIntoInput(kw) {
  const current = newsInput.value.trim();
  if (current) {
    newsInput.value = `${current} ${kw}`;
  } else {
    newsInput.value = kw;
  }
  updateInputMetrics();
  newsInput.focus();
}

// ============================================================
// THEME & EVENT HANDLERS
// ============================================================

function initTheme() {
  const savedTheme = localStorage.getItem(THEME_KEY);
  if (savedTheme) {
    document.documentElement.setAttribute("data-theme", savedTheme);
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

// Presets
document.getElementById("exampleFakeBtn").addEventListener("click", () => {
  newsInput.value = PRESETS.fake;
  updateInputMetrics();
  performCheck();
});

document.getElementById("exampleRealBtn").addEventListener("click", () => {
  newsInput.value = PRESETS.real;
  updateInputMetrics();
  performCheck();
});

document.getElementById("exampleNeutralBtn").addEventListener("click", () => {
  newsInput.value = PRESETS.neutral;
  updateInputMetrics();
  performCheck();
});

document.getElementById("exampleClickbaitBtn").addEventListener("click", () => {
  newsInput.value = PRESETS.clickbait;
  updateInputMetrics();
  performCheck();
});

// Clear Text & Reset
clearTextBtn.addEventListener("click", () => {
  newsInput.value = "";
  updateInputMetrics();
  newsInput.focus();
});

resetBtn.addEventListener("click", () => {
  newsInput.value = "";
  updateInputMetrics();
  validationMessage.classList.remove("active");
  activeResultState.classList.add("hidden");
  emptyResultState.classList.remove("hidden");
  verdictTimestamp.textContent = "Ready for input";
  currentAnalysis = null;
  newsInput.focus();
  showToast("Analyzer reset");
});

// Check News button
checkBtn.addEventListener("click", performCheck);

// Keyboard shortcuts (Ctrl+Enter to check)
newsInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    performCheck();
  }
});

newsInput.addEventListener("input", updateInputMetrics);

// Theme button
themeToggleBtn.addEventListener("click", toggleTheme);

// Clipboard Paste Button Handler (Copy from other websites)
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
    } catch (err) {
      console.warn("Clipboard access not allowed or unsupported:", err);
    }

    // Fallback prompt if clipboard permission is restricted
    const userPromptText = prompt("Paste your news text copied from any website or social media here:");
    if (userPromptText && userPromptText.trim()) {
      newsInput.value = userPromptText.trim();
      updateInputMetrics();
      performCheck();
      showToast("📋 Copied news pasted and analyzed!");
    }
  });
}

// Fetch Article from Website URL Button Handler
if (fetchUrlBtn) {
  fetchUrlBtn.addEventListener("click", async () => {
    const url = prompt("Enter a news article URL to inspect (e.g. https://www.bbc.com/news/...):");
    if (!url || !url.trim()) return;

    const trimmedUrl = url.trim();
    if (!/^https?:\/\//i.test(trimmedUrl)) {
      showToast("Please enter a valid URL starting with http:// or https://");
      return;
    }

    showToast("🔍 Fetching article from website URL...");

    try {
      // Use AllOrigins proxy to bypass browser cross-origin policy for public articles
      const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(trimmedUrl)}`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);

      const response = await fetch(proxyUrl, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        if (data && data.contents) {
          const parser = new DOMParser();
          const doc = parser.parseFromString(data.contents, "text/html");
          const ogTitle = doc.querySelector('meta[property="og:title"]')?.getAttribute("content")?.trim() || "";
          const docTitle = doc.querySelector("title")?.textContent?.trim() || "";
          const metaDesc = doc.querySelector('meta[name="description"]')?.getAttribute("content")?.trim() || 
                           doc.querySelector('meta[property="og:description"]')?.getAttribute("content")?.trim() || "";

          const headline = ogTitle || docTitle;
          if (headline) {
            const combined = metaDesc 
              ? `${headline} - ${metaDesc} (${trimmedUrl})` 
              : `${headline} (${trimmedUrl})`;
            newsInput.value = combined;
            updateInputMetrics();
            performCheck();
            showToast("✅ Article extracted from website & analyzed!");
            return;
          }
        }
      }
    } catch (e) {
      console.warn("URL extraction proxy unavailable or timed out:", e);
    }

    // Direct fallback: load URL into analyzer for domain reputation check
    newsInput.value = trimmedUrl;
    updateInputMetrics();
    performCheck();
    showToast("🔗 Website URL loaded for domain & credibility analysis!");
  });
}

// Copy Full Report Action
copyResultBtn.addEventListener("click", () => {
  if (!currentAnalysis) return;
  const advice = generateAdvice(currentAnalysis);
  const reasonsText = currentAnalysis.reasons.map(r => `• ${r.text}`).join("\n");
  const summary = `🛡️ FAKE NEWS DETECTOR ANALYSIS REPORT\n` +
    `-----------------------------------------\n` +
    `Statement: "${currentAnalysis.originalText}"\n` +
    `Verdict: ${currentAnalysis.verdict} (${currentAnalysis.cssClass.toUpperCase()})\n` +
    `Suspicion Score: ${currentAnalysis.fakeScore} | Credibility Score: ${currentAnalysis.realScore}\n\n` +
    `Key Findings:\n${reasonsText}\n\n` +
    `Advice & Recommendations:\n${advice.text}\n` +
    `-----------------------------------------\n` +
    `Analyzed via Fake News Detector: https://${window.location.host || "fake-news-detector-tau-roan.vercel.app"}`;

  navigator.clipboard.writeText(summary).then(() => {
    showToast("📋 Full analysis report copied to clipboard!");
  }).catch(() => {
    showToast("Failed to copy report.");
  });
});

// Share Action
shareResultBtn.addEventListener("click", () => {
  if (!currentAnalysis) return;
  if (navigator.share) {
    navigator.share({
      title: "Fake News Analysis",
      text: `Analysis: ${currentAnalysis.verdict} for "${currentAnalysis.originalText}"`,
      url: window.location.href
    }).catch(() => {});
  } else {
    copyResultBtn.click();
  }
});

// History filtering & clearing
historyFilters.addEventListener("click", (e) => {
  if (e.target.classList.contains("filter-btn")) {
    document.querySelectorAll(".filter-btn").forEach(btn => btn.classList.remove("active"));
    e.target.classList.add("active");
    renderHistory(e.target.dataset.filter);
  }
});

clearHistoryBtn.addEventListener("click", () => {
  if (historyState.length === 0) return;
  if (confirm("Are you sure you want to clear your analysis history?")) {
    historyState = [];
    saveHistory();
    renderHistory();
    showToast("History cleared");
  }
});

// Initialize on page load
window.addEventListener("DOMContentLoaded", () => {
  initTheme();
  populateKeywordClouds();
  loadHistory();
  updateInputMetrics();
});
