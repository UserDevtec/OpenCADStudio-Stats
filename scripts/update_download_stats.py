#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TARGET_REPO = os.environ.get("TARGET_REPO", "HakanSeven12/OpenCADStudio")
TARGET_TIMEZONE = os.environ.get("TARGET_TIMEZONE", "Europe/Amsterdam")

STATS_DIR = Path("stats")
HISTORY_FILE = STATS_DIR / "download-history.json"
SUMMARY_FILE = STATS_DIR / "downloads.json"

BADGES = {
    "today": STATS_DIR / "downloads-today.json",
    "hour": STATS_DIR / "downloads-hour.json",
    "week": STATS_DIR / "downloads-week.json",
    "latest": STATS_DIR / "downloads-latest-release.json",
    "total": STATS_DIR / "downloads-total.json",
}

API_BASE = f"https://api.github.com/repos/{TARGET_REPO}"


def github_get(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "download-stats-github-action",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"GitHub API returned HTTP {exc.code}: {body}", file=sys.stderr)
        raise


def get_all_releases():
    releases = []
    page = 1

    while True:
        batch = github_get(
            f"{API_BASE}/releases?per_page=100&page={page}"
        )

        if not batch:
            break

        releases.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    return releases


def asset_downloads(release):
    return sum(int(asset.get("download_count", 0)) for asset in release.get("assets", []))


def compact_number(value: int) -> str:
    value = int(value)

    if value < 1000:
        return f"{value:,}"

    if value < 1_000_000:
        number = value / 1000
        return f"{number:.1f}k".replace(".0k", "k")

    number = value / 1_000_000
    return f"{number:.1f}M".replace(".0M", "M")


def badge(label: str, value: int, color: str = "blue"):
    return {
        "schemaVersion": 1,
        "label": label,
        "message": compact_number(value),
        "color": color,
    }


def load_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def parse_timestamp(value: str):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def delta_since(history, current_total: int, since_utc: datetime):
    candidates = []

    for point in history:
        try:
            timestamp = parse_timestamp(point["timestamp"])
            total = int(point["total_downloads"])
        except (KeyError, TypeError, ValueError):
            continue

        if timestamp >= since_utc:
            candidates.append((timestamp, total))

    if candidates:
        _, baseline = min(candidates, key=lambda item: item[0])
        return max(0, current_total - baseline)

    # No historical measurement exists for this window yet.
    return 0


def write_json(path: Path, data):
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    STATS_DIR.mkdir(parents=True, exist_ok=True)

    releases = get_all_releases()

    if not releases:
        raise RuntimeError(f"No releases found for {TARGET_REPO}")

    published_releases = [
        release for release in releases
        if not release.get("draft", False)
    ]

    if not published_releases:
        raise RuntimeError(f"No published releases found for {TARGET_REPO}")

    latest = published_releases[0]
    latest_total = asset_downloads(latest)
    all_time_total = sum(asset_downloads(release) for release in published_releases)

    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    local_tz = ZoneInfo(TARGET_TIMEZONE)
    now_local = now_utc.astimezone(local_tz)

    history = load_history()

    # Add the latest snapshot before calculating deltas.
    snapshot = {
        "timestamp": now_utc.isoformat().replace("+00:00", "Z"),
        "total_downloads": all_time_total,
        "latest_release": latest.get("tag_name", ""),
        "latest_release_downloads": latest_total,
    }

    history.append(snapshot)

    # Keep approximately 8 days of 5-minute measurements.
    cutoff = now_utc - timedelta(days=8)
    cleaned_history = []

    for point in history:
        try:
            if parse_timestamp(point["timestamp"]) >= cutoff:
                cleaned_history.append(point)
        except (KeyError, TypeError, ValueError):
            continue

    history = cleaned_history

    start_today_local = now_local.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_today_utc = start_today_local.astimezone(timezone.utc)

    downloads_today = delta_since(history, all_time_total, start_today_utc)
    downloads_hour = delta_since(history, all_time_total, now_utc - timedelta(hours=1))
    downloads_week = delta_since(history, all_time_total, now_utc - timedelta(days=7))

    assets = [
        {
            "name": asset.get("name", ""),
            "downloads": int(asset.get("download_count", 0)),
            "url": asset.get("browser_download_url", ""),
        }
        for asset in latest.get("assets", [])
    ]

    summary = {
        "repository": TARGET_REPO,
        "timezone": TARGET_TIMEZONE,
        "updated": snapshot["timestamp"],
        "total_downloads": all_time_total,
        "downloads_today": downloads_today,
        "downloads_last_hour": downloads_hour,
        "downloads_last_7_days": downloads_week,
        "latest_release": {
            "tag": latest.get("tag_name", ""),
            "name": latest.get("name", ""),
            "published_at": latest.get("published_at", ""),
            "downloads": latest_total,
            "assets": assets,
        },
    }

    write_json(HISTORY_FILE, history)
    write_json(SUMMARY_FILE, summary)

    write_json(
        BADGES["today"],
        badge("downloads today", downloads_today, "brightgreen"),
    )
    write_json(
        BADGES["hour"],
        badge("downloads last hour", downloads_hour, "blue"),
    )
    write_json(
        BADGES["week"],
        badge("downloads last 7 days", downloads_week, "blue"),
    )
    write_json(
        BADGES["latest"],
        badge("latest release downloads", latest_total, "blue"),
    )
    write_json(
        BADGES["total"],
        badge("total downloads", all_time_total, "blue"),
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
