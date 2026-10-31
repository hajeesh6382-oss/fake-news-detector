# ============================================================
#  FAKE NEWS DETECTOR - COMPLETE WEBSITE IN ONE FILE
#  PART 1 = HTML (structure)
#  PART 2 = CSS  (style)
#  PART 3 = Python (backend)
#
#  Educational, rule-based prototype.
#  Uses only Python built-in libraries (no installation needed).
#
#  HOW TO RUN :  python fake_news_website.py
#  Then open  :  http://localhost:8000
#  To stop    :  press Ctrl + C in the terminal
#
#  NOTE: This program does NOT verify real news. It only looks
#  for suspicious / credible keywords and gives a PRELIMINARY
#  prediction, not a verified fact.
# ============================================================

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import html
import webbrowser

PORT = 8000


# ============================================================
#  PART 1 : HTML  (structure of the page)
#  {{TEXT}}, {{MESSAGE}}, {{RESULT}} and {{HISTORY}} are filled
#  in by the Python code in PART 3.
# ============================================================
HTML_CODE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fake News Detector</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>

  <header>
    <h1>Fake News Detector</h1>
    <p>Educational, rule-based prototype &ndash; results are preliminary
       predictions, NOT verified facts.</p>
  </header>

  <main>
    <!-- Input section -->
    <section class="card">
      <h3>Enter a news headline or statement</h3>
      <form method="POST" action="/">
        <textarea name="news" placeholder="Type or paste news here...">{{TEXT}}</textarea>
        <div class="message">{{MESSAGE}}</div>

        <button class="check" type="submit" name="action" value="check">Check News</button>
        <button class="clear" type="submit" name="action" value="clear">Clear</button>

        <p class="note">Try an example:</p>
        <button class="example" type="submit" name="action" value="ex0">Fake example</button>
        <button class="example" type="submit" name="action" value="ex1">Real example</button>
        <button class="example" type="submit" name="action" value="ex2">Neutral example</button>
      </form>
    </section>

    <!-- Result section (filled by Python) -->
    {{RESULT}}

    <!-- History section (all statements checked) -->
    <section class="card">
      <h3>Checked statements</h3>
      <ol>{{HISTORY}}</ol>
    </section>
  </main>

  <footer>Fake News Detector &ndash; Mini Project</footer>

</body>
</html>"""


# ============================================================
#  PART 2 : CSS  (style of the page)
# ============================================================
CSS_CODE = """/* ---------- Fake News Detector : style.css ---------- */

body {
  font-family: Arial, Helvetica, sans-serif;
  background: #f4f1f2;
  color: #222;
  margin: 0;
}

/* Title band */
header {
  background: #a3123a;
  color: #fff;
  text-align: center;
  padding: 22px 14px;
}
header h1 { margin: 0; font-size: 28px; }
header p  { margin: 6px 0 0; font-size: 14px; }

/* Main column */
main {
  max-width: 760px;
  margin: 20px auto;
  padding: 0 14px;
}

/* White boxes */
.card {
  background: #fff;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

/* Text box */
textarea {
  width: 100%;
  height: 100px;
  padding: 10px;
  font-size: 16px;
  box-sizing: border-box;
  border: 1px solid #aaa;
  border-radius: 6px;
}

/* Buttons */
button {
  padding: 10px 18px;
  font-size: 15px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  margin: 8px 8px 0 0;
}
.check   { background: #a3123a; color: #fff; }
.clear   { background: #ddd; }
.example { background: #eee; font-size: 13px; padding: 6px 10px; }

/* Result label */
.badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  color: #fff;
  font-weight: bold;
  font-size: 18px;
}
.fake   { background: #c62828; }   /* red    */
.real   { background: #2e7d32; }   /* green  */
.unsure { background: #ef6c00; }   /* orange */

/* Small texts */
.message { color: #c62828; margin-top: 8px; }
.note    { font-size: 13px; color: #555; }
footer   { text-align: center; font-size: 13px; color: #555; padding-bottom: 20px; }

/* Phone screens */
@media (max-width: 480px) {
  header h1 { font-size: 22px; }
}"""


# ============================================================
#  PART 3 : PYTHON  (backend)
# ============================================================
# Words and phrases that are often seen in misleading / fake posts
FAKE_KEYWORDS = [
    "shocking", "you won't believe", "miracle", "secret", "exposed",
    "hoax", "conspiracy", "100% cure", "share before", "forward this",
    "breaking!!!", "they don't want you to know", "free money",
    "instant cure", "leaked", "banned", "doctors hate", "guaranteed",
    "viral", "urgent"
]

# Words and phrases that are often seen in factual / formal reporting
REAL_KEYWORDS = [
    "according to", "official", "government", "ministry", "report",
    "published", "research", "study", "confirmed", "announced",
    "police", "university", "officials", "statement", "data",
    "survey", "press conference", "court", "department", "minister"
]

# Sentences used by the example buttons
EXAMPLES = [
    "SHOCKING!! Miracle cure exposed, share before it is banned",
    "According to the Ministry of Health, an official report was published today",
    "The weather is nice today"
]

# Remembers every statement checked (so many can be checked)
HISTORY = []


# ---------------- Detection logic ----------------
def count_matches(text, keyword_list):
    """Return a list of keywords from keyword_list found in the text."""
    found = []
    for word in keyword_list:
        if word in text:
            found.append(word)
    return found


def has_excessive_punctuation(text):
    """Check for '!!' or '??' style punctuation."""
    return "!!" in text or "??" in text


def is_mostly_capitals(original_text):
    """Return True if most of the letters in the text are capital letters."""
    letters = [ch for ch in original_text if ch.isalpha()]
    if len(letters) < 10:
        return False
    capitals = [ch for ch in letters if ch.isupper()]
    return len(capitals) / len(letters) > 0.7


def analyze_news(original_text):
    """Analyze the text and return (result, css_class, fake, real, reasons)."""
    text = original_text.lower()
    fake_found = count_matches(text, FAKE_KEYWORDS)
    real_found = count_matches(text, REAL_KEYWORDS)
    fake_score = len(fake_found)
    real_score = len(real_found)
    reasons = []

    # Extra suspicious style checks
    if has_excessive_punctuation(text):
        fake_score += 1
        reasons.append("It uses excessive punctuation (like !! or ??).")
    if is_mostly_capitals(original_text):
        fake_score += 1
        reasons.append("It is written mostly in CAPITAL LETTERS.")
    if fake_found:
        reasons.append("Suspicious words found: " + ", ".join(fake_found) + ".")
    if real_found:
        reasons.append("Credible-style words found: " + ", ".join(real_found) + ".")
    if not reasons:
        reasons.append("No suspicious or credible keywords were found.")

    # Decision rules
    if fake_score > real_score:
        result, css_class = "FAKE NEWS", "fake"
    elif real_score > fake_score:
        result, css_class = "LIKELY REAL NEWS", "real"
    else:
        result, css_class = "UNCERTAIN", "unsure"
        reasons.append("Not enough keywords to decide.")
    return result, css_class, fake_score, real_score, reasons


# ---------------- Page building ----------------
def build_page(text="", message="", result=None):
    """Put the text, message, result and history into the HTML code."""
    result_html = ""
    if result is not None:
        name, css_class, fake, real, reasons = result
        items = "".join("<li>" + html.escape(r) + "</li>" for r in reasons)
        result_html = (
            '<section class="card"><h3>Result</h3>'
            '<span class="badge ' + css_class + '">' + name + "</span>"
            "<p>Fake score = " + str(fake) + " &nbsp;|&nbsp; Real score = "
            + str(real) + "</p><p><b>Explanation:</b></p><ul>" + items + "</ul>"
            '<p class="note">This is only a keyword-based guess, '
            "not a fact check.</p></section>"
        )

    history_html = "".join(
        "<li>" + html.escape(t) + " --&gt; " + r + "</li>" for t, r in HISTORY
    )

    page = HTML_CODE
    page = page.replace("{{TEXT}}", html.escape(text))
    page = page.replace("{{MESSAGE}}", html.escape(message))
    page = page.replace("{{RESULT}}", result_html)
    page = page.replace("{{HISTORY}}", history_html)
    return page


# ---------------- Web server ----------------
class Handler(BaseHTTPRequestHandler):

    def send_content(self, content, content_type):
        """Send a page or file to the browser."""
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        """Browser asks for a page: send the HTML page or the CSS style."""
        if self.path == "/":
            self.send_content(build_page(), "text/html; charset=utf-8")
        elif self.path == "/style.css":
            self.send_content(CSS_CODE, "text/css; charset=utf-8")
        else:
            self.send_error(404, "Page not found")

    def do_POST(self):
        """Browser sent the form: check the news, clear or fill an example."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = parse_qs(body)
        action = data.get("action", [""])[0]
        news = data.get("news", [""])[0].strip()

        if action == "clear":
            page = build_page()
        elif action.startswith("ex"):
            page = build_page(text=EXAMPLES[int(action[2:])])
        elif news == "":
            page = build_page(message="Please enter some news text.")
        else:
            result = analyze_news(news)
            HISTORY.insert(0, (news, result[0]))
            page = build_page(text=news, result=result)
        self.send_content(page, "text/html; charset=utf-8")


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = "http://localhost:" + str(PORT)
    print("Fake News Detector is running at", url)
    print("Press Ctrl + C to stop.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWebsite stopped. Goodbye!")
        server.server_close()


# Program starts here
if __name__ == "__main__":
    main()
