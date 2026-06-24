#!/usr/bin/env python3
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "market-symbols.json"
DATA_DIR = ROOT / "data"
DAILY_PATH = DATA_DIR / "market.json"
INTRADAY_PATH = DATA_DIR / "intraday.json"
BASE_URL = "https://eodhd.com/api"


def load_json(path, fallback):
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(path)


def request_json(path, token, params):
    query = urllib.parse.urlencode({**params, "api_token": token, "fmt": "json"})
    request = urllib.request.Request(
        f"{BASE_URL}/{path}?{query}",
        headers={"User-Agent": "trade-review-mvp/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def date_string(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()


def unix_time(days_ago):
    return int((datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp())


def daily_rows(payload):
    if not isinstance(payload, list):
        return []
    rows = []
    for item in payload:
        try:
            rows.append({
                "date": str(item["date"])[:10],
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": float(item.get("volume") or 0),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(rows, key=lambda row: row["date"])


def intraday_rows(payload):
    if not isinstance(payload, list):
        return []
    rows = []
    for item in payload:
        try:
            timestamp = int(item.get("timestamp") or 0)
            moment = datetime.fromtimestamp(timestamp, timezone.utc)
            rows.append({
                "timestamp": timestamp,
                "datetime": item.get("datetime") or moment.isoformat(),
                "date": moment.date().isoformat(),
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": float(item.get("volume") or 0),
            })
        except (KeyError, TypeError, ValueError, OSError):
            continue
    return sorted(rows, key=lambda row: row["timestamp"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", choices=["all", "asia", "us"], default="all")
    parser.add_argument("--skip-intraday", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("EODHD_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing EODHD_API_TOKEN")

    config = load_json(CONFIG_PATH, {"symbols": [], "historyDays": 400, "intradayDays": 400})
    temporary_symbols = os.environ.get("MARKET_SYMBOLS_JSON", "").strip()
    if temporary_symbols:
        try:
            symbols = json.loads(temporary_symbols)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid MARKET_SYMBOLS_JSON: {error}") from error
        if not isinstance(symbols, list) or not 1 <= len(symbols) <= 3:
            raise SystemExit("MARKET_SYMBOLS_JSON must contain 1 to 3 symbols")
    else:
        symbols = [
            item for item in config.get("symbols", [])
            if args.session == "all" or item.get("session") == args.session
        ]
    if not symbols:
        print(f"No symbols configured for session: {args.session}")
        return

    now = datetime.now(timezone.utc).isoformat()
    daily_data = load_json(DAILY_PATH, {"updatedAt": None, "source": "EODHD", "symbols": {}})
    intraday_data = load_json(INTRADAY_PATH, {"updatedAt": None, "source": "EODHD", "symbols": {}})
    errors = []
    daily_updated = False
    intraday_updated = False

    for symbol in symbols:
        code = str(symbol["code"]).strip()
        eodhd = str(symbol["eodhd"]).strip()
        print(f"Updating {code} ({eodhd})")
        try:
            payload = request_json(
                f"eod/{urllib.parse.quote(eodhd)}",
                token,
                {
                    "from": date_string(int(config.get("historyDays", 400))),
                    "to": date_string(0),
                    "period": "d",
                    "order": "a",
                },
            )
            rows = daily_rows(payload)
            if not rows:
                raise ValueError("daily response contains no valid rows")
            daily_data["symbols"][code] = {
                "eodhd": eodhd,
                "name": symbol.get("name") or code,
                "updatedAt": now,
                "daily": rows,
            }
            daily_updated = True
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{code} daily: {error}")
        time.sleep(0.25)

        if args.skip_intraday:
            continue
        try:
            payload = request_json(
                f"intraday/{urllib.parse.quote(eodhd)}",
                token,
                {
                    "interval": "5m",
                    "from": unix_time(int(config.get("intradayDays", 400))),
                    "to": unix_time(0),
                },
            )
            rows = intraday_rows(payload)
            if not rows:
                raise ValueError("intraday response contains no valid rows")
            intraday_data["symbols"][code] = {
                "eodhd": eodhd,
                "name": symbol.get("name") or code,
                "updatedAt": now,
                "points": rows,
            }
            intraday_updated = True
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{code} intraday: {error}")
        time.sleep(0.25)

    if daily_updated:
        daily_data["updatedAt"] = now
    if intraday_updated:
        intraday_data["updatedAt"] = now
    save_json(DAILY_PATH, daily_data)
    save_json(INTRADAY_PATH, intraday_data)

    if errors:
        print("Some requests were skipped:")
        for error in errors:
            print(f"- {error}")
    print(f"Saved {DAILY_PATH.relative_to(ROOT)} and {INTRADAY_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
