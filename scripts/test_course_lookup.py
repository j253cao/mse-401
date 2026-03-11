#!/usr/bin/env python3
"""Quick verification of course code search in /recommend endpoint."""
import urllib.request
import json


def test(q):
    data = json.dumps({"queries": [q], "filters": {}}).encode()
    req = urllib.request.Request(
        "http://localhost:8000/recommend",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        out = json.load(resp)
        results = out["results"].get(q, [])
        codes = [r["course_code"] for r in results]
        print(f'Query "{q}": {len(results)} results -> {codes[:5]}{"..." if len(codes) > 5 else ""}')
        return results


if __name__ == "__main__":
    print("=== Course code search verification ===\n")
    test("MSE446")
    test("MSE 446")
    test("446")
    test("123")
    r = test("machine learning")
    print("  (first 2 codes):", [x["course_code"] for x in r[:2]])
    r = test("12")
    print("  (first 2 codes):", [x["course_code"] for x in r[:2]])
    print("\nDone.")
