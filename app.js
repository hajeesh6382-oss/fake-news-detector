/**
 * FAKE NEWS DETECTOR - FRONTEND ENGINE & LINGUISTIC HEURISTICS
 * Faithfully mirrors the Python rule engine with client-side interactive enhancements.
 */

// ============================================================
// KEYWORD DICTIONARIES (identical to Python prototype)
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

// Presets for quick evaluation
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
// DETECTION ALGORITHM (Matching Python Logic)
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
  const fakeFound = countMatches(text, FAKE_KEYWORDS);
  const realFound = countMatches(text, REAL_KEYWORDS);
  
  let fakeScore = fakeFound.length;
  let realScore = realFound.length;
  const reasons = [];

  // Style heuristics
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
    fakeFound,
    realFound,
    subtitle,
    timestamp: new Date()
  };
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
  let text = result.originalText;
  
  // Collect all spans to highlight
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
  // Avoid duplicate if same as first
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

  // Limit to last 50 items
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

// Copy & Share Actions
copyResultBtn.addEventListener("click", () => {
  if (!currentAnalysis) return;
  const summary = `🛡️ Fake News Detector Result\nStatement: "${currentAnalysis.originalText}"\nVerdict: ${currentAnalysis.verdict}\nSuspicion Score: ${currentAnalysis.fakeScore} | Credibility Score: ${currentAnalysis.realScore}\nhttps://${window.location.host}`;
  navigator.clipboard.writeText(summary).then(() => {
    showToast("Analysis copied to clipboard!");
  }).catch(() => {
    showToast("Failed to copy result.");
  });
});

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
