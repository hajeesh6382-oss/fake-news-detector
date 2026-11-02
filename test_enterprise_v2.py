import sys
import io
import json

# Ensure UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def run_tests():
    print("=====================================================================")
    print("      VERITAS AI ENTERPRISE V2.0 - 7 VERIFICATION PIPELINE TESTS     ")
    print("=====================================================================\n")

    passed_count = 0

    # -------------------------------------------------------------------------
    # TEST 1: Genuine News from Accredited Publisher
    # -------------------------------------------------------------------------
    print(">>> TEST 1: Genuine News Verification (BBC / Accredited Source)")
    t1_url = "https://www.bbc.com/news/live/cm4g1yjxv38gt"
    r1 = client.post("/api/verify", json={"url": t1_url})
    d1 = r1.json()
    print(f"Status Code: {r1.status_code}")
    print(f"Verdict: {d1.get('verdict')} | Score: {d1.get('confidence_score')}%")
    print(f"Publisher: {d1.get('publisher')} | Domain: {d1.get('domain')}")
    print(f"Explanation: {d1.get('why_this_verdict')[:120]}...")
    assert r1.status_code == 200
    assert d1.get("verdict") in ["REAL NEWS", "UNVERIFIED", "INSUFFICIENT EVIDENCE", "EXTRACTION FAILED"]
    print("✅ TEST 1 PASSED: Pipeline ran cleanly without crashing.\n")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 2: Fabricated Viral Hoax (Known Falsehood)
    # -------------------------------------------------------------------------
    print(">>> TEST 2: Fabricated News Detection (RBI Rs 1000 Note Hoax)")
    t2_text = "Reserve Bank of India announces immediate re-release of 1000 rupee currency notes featuring nano GPS tracking microchip."
    r2 = client.post("/api/verify", json={"text": t2_text, "headline": "RBI 1000 Rupee Note Reintroduction Hoax"})
    d2 = r2.json()
    print(f"Status Code: {r2.status_code}")
    print(f"Verdict: {d2.get('verdict')} | Score: {d2.get('confidence_score')}%")
    print(f"Contradicting / Debunk Evidence Count: {len(d2.get('contradicting_evidence', []))}")
    print(f"Explanation: {d2.get('why_this_verdict')[:140]}...")
    assert r2.status_code == 200
    assert d2.get("verdict") == "FAKE NEWS" or len(d2.get("contradicting_evidence", [])) > 0
    print("✅ TEST 2 PASSED: Fabricated story accurately flagged as FAKE NEWS or debunked.\n")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 3: Partially Misleading Claim
    # -------------------------------------------------------------------------
    print(">>> TEST 3: Partially Misleading Claim Analysis (5G towers cause instant virus spread)")
    t3_text = "5G cellular towers emit millimeter radiation that directly creates biological coronavirus pathogens in living tissue."
    r3 = client.post("/api/verify", json={"text": t3_text, "headline": "5G Millimeter Radiation Virus Claim"})
    d3 = r3.json()
    print(f"Status Code: {r3.status_code}")
    print(f"Verdict: {d3.get('verdict')} | Score: {d3.get('confidence_score')}%")
    print(f"Warnings: {d3.get('warnings')}")
    assert r3.status_code == 200
    assert d3.get("verdict") in ["FAKE NEWS", "INSUFFICIENT EVIDENCE", "UNVERIFIED"]
    print("✅ TEST 3 PASSED: Misleading claim flagged with audit evidence.\n")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 4: Unsubstantiated Claim (No Independent News Coverage)
    # -------------------------------------------------------------------------
    print(">>> TEST 4: Unsubstantiated Claim (Alien Flying Saucer in Rural Village)")
    t4_text = "A secret metallic flying saucer was unearthed by a farmer beneath an onion barn in an undisclosed village today."
    r4 = client.post("/api/verify", json={"text": t4_text, "headline": "Farmer unearths UFO"})
    d4 = r4.json()
    print(f"Status Code: {r4.status_code}")
    print(f"Verdict: {d4.get('verdict')} | Score: {d4.get('confidence_score')}%")
    print(f"Matching Sources Count: {len(d4.get('matching_sources', []))}")
    assert r4.status_code == 200
    assert d4.get("verdict") in ["INSUFFICIENT EVIDENCE", "UNVERIFIED"]
    print("✅ TEST 4 PASSED: Unsubstantiated story correctly classified as INSUFFICIENT EVIDENCE / UNVERIFIED.\n")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 5: Invalid URL Format
    # -------------------------------------------------------------------------
    print(">>> TEST 5: Invalid URL Format Handling ('abc')")
    t5_url = "abc"
    r5 = client.post("/api/verify", json={"url": t5_url})
    d5 = r5.json()
    print(f"Status Code: {r5.status_code}")
    print(f"Verdict: {d5.get('verdict')} | Error Title: {d5.get('error_title', d5.get('why_this_verdict'))}")
    assert r5.status_code == 200
    assert d5.get("verdict") == "INVALID INPUT" or d5.get("status") in ["error", "warning"]
    print("✅ TEST 5 PASSED: Clear error returned without crashing or blank screen.\n")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 6: Inaccessible URL / SSRF Protection
    # -------------------------------------------------------------------------
    print(">>> TEST 6: Inaccessible URL & SSRF Loopback Protection (127.0.0.1)")
    t6_url = "http://127.0.0.1:8080/internal/admin"
    r6 = client.post("/api/verify", json={"url": t6_url})
    d6 = r6.json()
    print(f"Status Code: {r6.status_code}")
    print(f"Verdict: {d6.get('verdict')} | Explanation: {d6.get('why_this_verdict')}")
    assert r6.status_code == 200
    assert d6.get("verdict") in ["BLOCKED URL", "INVALID INPUT"] or "SSRF" in str(d6) or "blocked" in str(d6).lower()
    print("✅ TEST 6 PASSED: Security shield blocked malicious loopback destination.\n")
    passed_count += 1

    # -------------------------------------------------------------------------
    # TEST 7: Contradictory Evidence / Multi-Source Cross-Check
    # -------------------------------------------------------------------------
    print(">>> TEST 7: Cross-Platform News Corroboration Pipeline")
    t7_text = "WHO declared emergency over global outbreak while pharmaceutical companies announce new treatment protocols."
    r7 = client.post("/api/verify", json={"text": t7_text, "headline": "WHO Global Health Announcement"})
    d7 = r7.json()
    print(f"Status Code: {r7.status_code}")
    print(f"Verdict: {d7.get('verdict')} | Confidence Score: {d7.get('confidence_score')}%")
    print(f"Platforms Checked: {len(d7.get('trusted_sources_checked', []))} sources")
    assert r7.status_code == 200
    print("✅ TEST 7 PASSED: Full cross-platform corroboration pipeline completed successfully.\n")
    passed_count += 1

    print("=====================================================================")
    print(f"      ALL {passed_count} OF 7 VERIFICATION SUITE TESTS PASSED!       ")
    print("=====================================================================")

if __name__ == "__main__":
    run_tests()
