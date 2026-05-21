#!/usr/bin/env python3
"""
verify_feeds.py — checks every RSS URL in sources.yaml and reports status.

Usage:
    pip install pyyaml requests
    python3 verify_feeds.py

Output:
    - Console table with status per feed
    - sources_report.md — markdown report
    - sources_report.json — machine-readable for later automation
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import yaml
    import requests
except ImportError:
    print("Install deps:  pip install pyyaml requests")
    sys.exit(1)

SOURCES_FILE = Path(__file__).parent / "sources.yaml"
REPORT_MD = Path(__file__).parent / "sources_report.md"
REPORT_JSON = Path(__file__).parent / "sources_report.json"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) DesignDigestUA/1.0"
TIMEOUT = 15
PARALLEL = 12


def flatten(cfg: dict) -> list[dict]:
    """Walk yaml tree and yield every source entry with its full path."""
    out = []
    for layer_name, categories in cfg.items():
        if layer_name == "dead":
            continue
        if not isinstance(categories, dict):
            continue
        for cat_name, items in categories.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and "url" in item:
                    item["_layer"] = layer_name
                    item["_category"] = cat_name
                    out.append(item)
    return out


def check_one(src: dict) -> dict:
    """Hit URL, classify response."""
    url = src["url"]
    name = src["name"]
    result = {
        "name": name,
        "url": url,
        "layer": src["_layer"],
        "category": src["_category"],
        "status": "unknown",
        "http_code": None,
        "is_feed": False,
        "item_count": 0,
        "latency_ms": None,
        "error": None,
    }
    start = time.time()
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
        result["http_code"] = r.status_code
        result["latency_ms"] = int((time.time() - start) * 1000)
        if r.status_code != 200:
            result["status"] = f"http_{r.status_code}"
            return result
        text = r.text[:50000]
        # Detect feed type
        if re.search(r"<(rss|feed)\b", text, re.IGNORECASE):
            result["is_feed"] = True
            items = re.findall(r"<(item|entry)\b", text, re.IGNORECASE)
            result["item_count"] = len(items)
            if result["item_count"] == 0:
                result["status"] = "feed_empty"
            elif result["item_count"] < 3:
                result["status"] = "feed_sparse"
            else:
                result["status"] = "ok"
        else:
            result["status"] = "not_a_feed"
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = "timeout"
    except requests.exceptions.SSLError as e:
        result["status"] = "ssl_error"
        result["error"] = str(e)[:200]
    except requests.exceptions.ConnectionError as e:
        result["status"] = "conn_error"
        result["error"] = str(e)[:200]
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {e}"[:200]
    return result


def render_console(results: list[dict]):
    by_status = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    print()
    print("=" * 100)
    print(f"  Design Digest UA — feed verification ({len(results)} sources)")
    print("=" * 100)
    summary = {k: len(v) for k, v in by_status.items()}
    ok = summary.get("ok", 0)
    print(f"\nSummary: {ok}/{len(results)} working\n")
    for status, count in sorted(summary.items(), key=lambda x: -x[1]):
        icon = "✓" if status == "ok" else "✗" if status.startswith(("http_", "conn", "ssl", "timeout", "error", "not_a_feed")) else "~"
        print(f"  {icon} {status:<20} {count}")

    print("\nDetails (problems first):")
    print("-" * 100)
    results_sorted = sorted(results, key=lambda r: (r["status"] == "ok", r["layer"], r["name"]))
    for r in results_sorted:
        mark = "OK " if r["status"] == "ok" else "!! "
        items = f"{r['item_count']:>3}it" if r["is_feed"] else "  - "
        lat = f"{r['latency_ms']}ms" if r["latency_ms"] else "  -  "
        print(f"  {mark}{r['status']:<14} {items} {lat:>6}  {r['name'][:35]:<35} {r['url']}")


def render_markdown(results: list[dict]) -> str:
    total = len(results)
    ok = sum(1 for r in results if r["status"] == "ok")
    lines = [
        f"# Sources Verification Report",
        "",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M')}",
        f"**Status:** {ok}/{total} feeds working ({ok*100//total}%)",
        "",
        "## By layer",
        "",
    ]
    by_layer = {}
    for r in results:
        by_layer.setdefault(r["layer"], []).append(r)

    for layer, items in by_layer.items():
        ok_n = sum(1 for r in items if r["status"] == "ok")
        lines.append(f"### {layer} — {ok_n}/{len(items)} working")
        lines.append("")
        lines.append("| Status | Items | Source | URL |")
        lines.append("|--------|------:|--------|-----|")
        for r in sorted(items, key=lambda r: (r["status"] != "ok", r["name"])):
            mark = "✅" if r["status"] == "ok" else "❌"
            items_s = str(r["item_count"]) if r["is_feed"] else "—"
            lines.append(f"| {mark} {r['status']} | {items_s} | {r['name']} | `{r['url']}` |")
        lines.append("")

    # Broken section with replacement suggestions
    broken = [r for r in results if r["status"] != "ok"]
    if broken:
        lines.append("## ❌ Broken — needs replacement")
        lines.append("")
        lines.append("Common fixes:")
        lines.append("- `404` → check current URL on the site's footer (look for RSS icon)")
        lines.append("- `not_a_feed` → URL is HTML, not RSS. Use rss.app to convert.")
        lines.append("- `conn_error` / `ssl_error` → site may be down or moved")
        lines.append("- `timeout` → retry in 1 hour; if persists, replace")
        lines.append("")
        for r in broken:
            lines.append(f"- **{r['name']}** ({r['layer']}/{r['category']}) — `{r['status']}` — {r['url']}")
        lines.append("")

    return "\n".join(lines)


def main():
    if not SOURCES_FILE.exists():
        print(f"sources.yaml not found at {SOURCES_FILE}")
        sys.exit(1)

    with open(SOURCES_FILE) as f:
        cfg = yaml.safe_load(f)

    sources = flatten(cfg)
    print(f"Checking {len(sources)} feeds with {PARALLEL} parallel workers...\n")

    results = []
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        futures = {pool.submit(check_one, s): s for s in sources}
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            results.append(r)
            mark = "✓" if r["status"] == "ok" else "✗"
            print(f"  [{i:>2}/{len(sources)}] {mark} {r['status']:<14} {r['name']}")

    render_console(results)

    REPORT_MD.write_text(render_markdown(results))
    REPORT_JSON.write_text(json.dumps(results, indent=2))
    print(f"\nReports:")
    print(f"  {REPORT_MD}")
    print(f"  {REPORT_JSON}")


if __name__ == "__main__":
    main()
