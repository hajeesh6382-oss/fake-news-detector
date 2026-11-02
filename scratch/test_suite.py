import os
import sys
import unittest

# Ensure workspace root in path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from backend.main import unified_verify, UnifiedVerificationRequest

def run_test_suite():
    print("=" * 70)
    print("VERITAS AI ENTERPRISE v2.0 - 6-TEST VERIFICATION SUITE")
    print("=" * 70)

    results = []

    # -------------------------------------------------------------
    # Test 1: BBC Live coverage URL (fallback metadata & live blog)
    # -------------------------------------------------------------
    url_1 = "https://www.bbc.com/news/live/cm4g1yjxv38gt"
    print(f"\n[Test 1] Input: {url_1}")
    res1 = unified_verify(UnifiedVerificationRequest(url=url_1))
    print(f"  Verdict: {res1.get('verdict')}")
    print(f"  Score: {res1.get('score')}")
    print(f"  Headline: {res1.get('headline')}")
    print(f"  Publisher: {res1.get('publisher')}")
    print(f"  Matching Sources: {len(res1.get('matching_sources', []))}")
    assert res1.get("verdict") in ("VERIFIED REAL", "LIKELY REAL"), "Test 1 failed verdict check"
    assert res1.get("headline"), "Test 1 headline is empty"
    results.append(("Test 1: BBC Live URL", "PASSED", f"Verdict: {res1.get('verdict')} (Score: {res1.get('score')})"))

    # -------------------------------------------------------------
    # Test 2: Normal bbc.com/news article URL
    # -------------------------------------------------------------
    url_2 = "https://www.bbc.com/news/world"
    print(f"\n[Test 2] Input: {url_2}")
    res2 = unified_verify(UnifiedVerificationRequest(url=url_2))
    sources2 = res2.get("matching_sources", [])
    print(f"  Verdict: {res2.get('verdict')}")
    print(f"  Publisher: {res2.get('publisher')}")
    print(f"  Matching Sources Count: {len(sources2)}")
    assert len(sources2) >= 2 or res2.get("score") >= 55, "Test 2 did not match criteria"
    results.append(("Test 2: Normal BBC URL", "PASSED", f"Verdict: {res2.get('verdict')} with {len(sources2)} matching sources"))

    # -------------------------------------------------------------
    # Test 3: Normal thehindu.com article URL
    # -------------------------------------------------------------
    url_3 = "https://www.thehindu.com/news/national/"
    print(f"\n[Test 3] Input: {url_3}")
    res3 = unified_verify(UnifiedVerificationRequest(url=url_3))
    sources3 = res3.get("matching_sources", [])
    print(f"  Verdict: {res3.get('verdict')}")
    print(f"  Publisher: {res3.get('publisher')}")
    print(f"  Matching Sources Count: {len(sources3)}")
    assert len(sources3) >= 1 and res3.get("score") >= 55, "Test 3 did not match criteria"
    results.append(("Test 3: Normal The Hindu URL", "PASSED", f"Verdict: {res3.get('verdict')} with {len(sources3)} matching sources"))

    # -------------------------------------------------------------
    # Test 4: Known debunked claim (new Rs 1000 note)
    # -------------------------------------------------------------
    claim_4 = "RBI announces introduction of new Rs 1000 note in market"
    print(f"\n[Test 4] Input claim: '{claim_4}'")
    res4 = unified_verify(UnifiedVerificationRequest(text=claim_4))
    print(f"  Verdict: {res4.get('verdict')}")
    print(f"  Score: {res4.get('score')}")
    print(f"  Why: {res4.get('why_this_verdict')}")
    has_pib = "PIB" in res4.get("why_this_verdict", "") or any("PIB" in str(s) for s in res4.get("matching_sources", []))
    assert res4.get("verdict") == "LIKELY FAKE", "Test 4 failed LIKELY FAKE verdict check"
    assert has_pib, "Test 4 missing PIB reference"
    results.append(("Test 4: Debunked 'new Rs 1000 note'", "PASSED", f"Verdict: {res4.get('verdict')} with PIB Fact Check reference"))

    # -------------------------------------------------------------
    # Test 5: Invalid text 'abc'
    # -------------------------------------------------------------
    text_5 = "abc"
    print(f"\n[Test 5] Input: '{text_5}'")
    res5 = unified_verify(UnifiedVerificationRequest(text=text_5))
    print(f"  Status: {res5.get('status')}")
    print(f"  Error Title: {res5.get('error_title')}")
    print(f"  Reason: {res5.get('reason')}")
    print(f"  Suggestion: {res5.get('suggestion')}")
    assert res5.get("status") == "error", "Test 5 did not return error status"
    assert res5.get("error_title") and res5.get("suggestion"), "Test 5 missing clear error card fields"
    results.append(("Test 5: Invalid text 'abc'", "PASSED", f"Error card rendered: '{res5.get('error_title')}' - {res5.get('reason')}"))

    # -------------------------------------------------------------
    # Test 6: Blocked or timed-out page
    # -------------------------------------------------------------
    url_6 = "https://192.0.2.1/news/breaking-story"
    print(f"\n[Test 6] Input timed-out URL: '{url_6}'")
    res6 = unified_verify(UnifiedVerificationRequest(url=url_6))
    print(f"  Status: {res6.get('status')}")
    print(f"  Verdict: {res6.get('verdict')}")
    print(f"  Why: {res6.get('why_this_verdict')}")
    assert res6.get("verdict") == "UNVERIFIED" or res6.get("status") in ("warning", "error"), "Test 6 failed"
    results.append(("Test 6: Blocked or timed-out page", "PASSED", f"Verdict: {res6.get('verdict')} with reason '{res6.get('why_this_verdict') or res6.get('reason')}'"))

    print("\n" + "=" * 70)
    print("ALL 6 TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    for test_name, status, details in results:
        print(f" [PASS] {test_name}: {details}")

if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    run_test_suite()
