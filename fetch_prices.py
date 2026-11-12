"""Fetch end-of-day prices for Conor's watchlist from Yahoo Finance.

Writes prices.json: latest close, previous close, day change,
1-year change and one year of daily closes for each ticker.
Standard library only, so the GitHub Action needs no installs.
"""

import json
import time
import urllib.request
from datetime import datetime, timezone

# Edit this list to change the watchlist. Yahoo uses .AX for ASX tickers.
WATCHLIST = [
    {"symbol": "^AXJO",    "code": "ASX200", "name": "S&P/ASX 200",                       "group": "market"},
    {"symbol": "^GSPC",    "code": "SPX",    "name": "S&P 500 (US)",                      "group": "market"},
    {"symbol": "AUDUSD=X", "code": "AUDUSD", "name": "AUD/USD",                           "group": "market"},
    {"symbol": "IOZ.AX",   "code": "IOZ",    "name": "iShares Core S&P/ASX 200",          "group": "etf", "platform": "Pocket"},
    {"symbol": "DHHF.AX",  "code": "DHHF",   "name": "Betashares Diversified All Growth", "group": "etf", "platform": "Pocket"},
    {"symbol": "A200.AX",  "code": "A200",   "name": "Betashares Australia 200",          "group": "etf", "platform": "CommSec"},
    {"symbol": "VGS.AX",   "code": "VGS",    "name": "Vanguard MSCI Intl Shares",         "group": "etf", "platform": "CommSec"},
    {"symbol": "BGBL.AX",  "code": "BGBL",   "name": "Betashares Global Shares",          "group": "etf", "platform": "CommSec"},
]

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1y&interval=1d"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; asx-prices/1.0)"}


def fetch(symbol):
    req = urllib.request.Request(URL.format(sym=urllib.request.quote(symbol)), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    result = data["chart"]["result"][0]
    stamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    tz_offset = result["meta"].get("gmtoffset", 0)

    history = []
    for ts, close in zip(stamps, closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(ts + tz_offset, tz=timezone.utc).strftime("%Y-%m-%d")
        history.append({"date": day, "close": round(close, 4)})

    # Drop a duplicate final row (Yahoo sometimes repeats today's bar)
    dedup = {}
    for row in history:
        dedup[row["date"]] = row["close"]
    history = [{"date": d, "close": c} for d, c in sorted(dedup.items())]

    last = history[-1]
    prev = history[-2] if len(history) > 1 else last
    first = history[0]
    return {
        "lastClose": last["close"],
        "lastDate": last["date"],
        "prevClose": prev["close"],
        "dayChangePct": round((last["close"] / prev["close"] - 1) * 100, 2),
        "oneYearChangePct": round((last["close"] / first["close"] - 1) * 100, 2),
        "oneYearFrom": first["date"],
        "high52w": max(r["close"] for r in history),
        "low52w": min(r["close"] for r in history),
        "currency": result["meta"].get("currency"),
        "history": history,
    }


def main():
    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Yahoo Finance chart API (end-of-day closes, unofficial)",
        "items": [],
    }
    for item in WATCHLIST:
        entry = dict(item)
        try:
            entry.update(fetch(item["symbol"]))
            entry["ok"] = True
        except Exception as exc:  # keep going if one ticker fails
            entry["ok"] = False
            entry["error"] = str(exc)[:200]
        out["items"].append(entry)
        time.sleep(1)

    with open("prices.json", "w") as f:
        json.dump(out, f, indent=1)

    failed = [i["code"] for i in out["items"] if not i["ok"]]
    print("Done.", "Failed: " + ", ".join(failed) if failed else "All tickers OK.")


if __name__ == "__main__":
    main()
