#!/usr/bin/env python3

import html
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

API_BASE = f"https://api.github.com/repos/{TARGET_REPO}"
MAX_HISTORY_DAYS = 30

BADGES = {
    "today": STATS_DIR / "downloads-today.json",
    "hour": STATS_DIR / "downloads-hour.json",
    "week": STATS_DIR / "downloads-week.json",
    "latest": STATS_DIR / "downloads-latest-release.json",
    "total": STATS_DIR / "downloads-total.json",
}

GRAPHS = {
    "24h": STATS_DIR / "download-growth-24h.svg",
    "7d": STATS_DIR / "download-growth-7d.svg",
    "30d": STATS_DIR / "download-growth-30d.svg",
}


def github_get(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "opencadstudio-download-growth-action",
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
        batch = github_get(f"{API_BASE}/releases?per_page=100&page={page}")

        if not batch:
            break

        releases.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    return releases


def asset_downloads(release):
    return sum(
        int(asset.get("download_count", 0))
        for asset in release.get("assets", [])
    )


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
            value = json.load(file)
            return value if isinstance(value, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def parse_timestamp(value: str):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def valid_history(history):
    result = []

    for point in history:
        try:
            timestamp = parse_timestamp(point["timestamp"])
            total = int(point["total_downloads"])
        except (KeyError, TypeError, ValueError):
            continue

        result.append({
            **point,
            "_timestamp": timestamp,
            "_total": total,
        })

    result.sort(key=lambda item: item["_timestamp"])
    return result


def baseline_at(history, since_utc):
    before = [p for p in history if p["_timestamp"] <= since_utc]
    if before:
        return max(before, key=lambda p: p["_timestamp"])["_total"]

    after = [p for p in history if p["_timestamp"] > since_utc]
    if after:
        return min(after, key=lambda p: p["_timestamp"])["_total"]

    return None


def delta_since(history, current_total, since_utc):
    baseline = baseline_at(history, since_utc)
    if baseline is None:
        return 0
    return max(0, current_total - baseline)


def write_json(path: Path, data):
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def nice_int(value):
    return f"{int(round(value)):,}"


def graph_svg(points, title, subtitle, current_total, period_growth):
    width = 1200
    height = 430

    left = 86
    right = 34
    top = 112
    bottom = 58

    plot_w = width - left - right
    plot_h = height - top - bottom

    if len(points) < 2:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="18" fill="#0d1117"/>
<text x="48" y="62" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="28" font-weight="700">{html.escape(title)}</text>
<text x="48" y="98" fill="#8b949e" font-family="Arial, sans-serif" font-size="18">Collecting history. The line appears after the second measurement.</text>
</svg>
'''

    times = [p["_timestamp"].timestamp() for p in points]
    values = [p["_total"] for p in points]

    min_x = min(times)
    max_x = max(times)
    min_y_raw = min(values)
    max_y_raw = max(values)

    if max_x == min_x:
        max_x = min_x + 1

    spread = max_y_raw - min_y_raw
    pad = max(5, int(spread * 0.12))
    min_y = max(0, min_y_raw - pad)
    max_y = max_y_raw + pad

    if max_y == min_y:
        max_y += 1

    def x_pos(ts):
        return left + ((ts - min_x) / (max_x - min_x)) * plot_w

    def y_pos(value):
        return top + (1 - ((value - min_y) / (max_y - min_y))) * plot_h

    coords = [
        (x_pos(p["_timestamp"].timestamp()), y_pos(p["_total"]))
        for p in points
    ]

    line_path = " ".join(
        ("M" if i == 0 else "L") + f" {x:.2f} {y:.2f}"
        for i, (x, y) in enumerate(coords)
    )

    area_path = (
        line_path
        + f" L {coords[-1][0]:.2f} {top + plot_h:.2f}"
        + f" L {coords[0][0]:.2f} {top + plot_h:.2f} Z"
    )

    grid_lines = []
    labels = []

    for i in range(5):
        ratio = i / 4
        y = top + ratio * plot_h
        value = max_y - ratio * (max_y - min_y)

        grid_lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" '
            f'stroke="#30363d" stroke-width="1"/>'
        )
        labels.append(
            f'<text x="{left - 14}" y="{y + 5:.2f}" text-anchor="end" '
            f'fill="#8b949e" font-family="Arial, sans-serif" font-size="14">{nice_int(value)}</text>'
        )

    local_tz = ZoneInfo(TARGET_TIMEZONE)
    start_dt = points[0]["_timestamp"].astimezone(local_tz)
    end_dt = points[-1]["_timestamp"].astimezone(local_tz)
    middle_dt = start_dt + (end_dt - start_dt) / 2

    x_labels = [
        (left, start_dt.strftime("%d %b %H:%M"), "start"),
        (left + plot_w / 2, middle_dt.strftime("%d %b %H:%M"), "middle"),
        (left + plot_w, end_dt.strftime("%d %b %H:%M"), "end"),
    ]

    x_text = []
    for x, label, anchor in x_labels:
        x_text.append(
            f'<text x="{x:.2f}" y="{height - 22}" text-anchor="{anchor}" '
            f'fill="#8b949e" font-family="Arial, sans-serif" font-size="14">{html.escape(label)}</text>'
        )

    end_x, end_y = coords[-1]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs>
  <linearGradient id="area" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0%" stop-color="#58a6ff" stop-opacity="0.28"/>
    <stop offset="100%" stop-color="#58a6ff" stop-opacity="0.02"/>
  </linearGradient>
</defs>

<rect width="100%" height="100%" rx="18" fill="#0d1117"/>

<text x="48" y="48" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="27" font-weight="700">{html.escape(title)}</text>
<text x="48" y="79" fill="#8b949e" font-family="Arial, sans-serif" font-size="16">{html.escape(subtitle)}</text>

<text x="{width - 48}" y="46" text-anchor="end" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="25" font-weight="700">{html.escape(compact_number(current_total))}</text>
<text x="{width - 48}" y="76" text-anchor="end" fill="#3fb950" font-family="Arial, sans-serif" font-size="17" font-weight="700">+{html.escape(compact_number(period_growth))} growth</text>

{''.join(grid_lines)}
{''.join(labels)}

<path d="{area_path}" fill="url(#area)"/>
<path d="{line_path}" fill="none" stroke="#58a6ff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="{end_x:.2f}" cy="{end_y:.2f}" r="6" fill="#58a6ff"/>
<circle cx="{end_x:.2f}" cy="{end_y:.2f}" r="11" fill="none" stroke="#58a6ff" stroke-opacity="0.28" stroke-width="5"/>

{''.join(x_text)}
</svg>
'''


def write_growth_graph(history, now_utc, period, path, title):
    since = now_utc - period
    points = [p for p in history if p["_timestamp"] >= since]

    if not points and history:
        points = history[-1:]

    current_total = history[-1]["_total"] if history else 0
    growth = delta_since(history, current_total, since)

    subtitle = f"{TARGET_REPO} cumulative GitHub Release asset downloads"
    path.write_text(
        graph_svg(points, title, subtitle, current_total, growth),
        encoding="utf-8",
    )


def main():
    STATS_DIR.mkdir(parents=True, exist_ok=True)

    releases = get_all_releases()

    published = [
        release
        for release in releases
        if not release.get("draft", False)
    ]

    if not published:
        raise RuntimeError(f"No published releases found for {TARGET_REPO}")

    stable = [
        release
        for release in published
        if not release.get("prerelease", False)
    ]

    latest = stable[0] if stable else published[0]

    latest_total = asset_downloads(latest)
    all_time_total = sum(asset_downloads(release) for release in published)

    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    local_tz = ZoneInfo(TARGET_TIMEZONE)
    now_local = now_utc.astimezone(local_tz)

    history_raw = load_history()

    snapshot = {
        "timestamp": now_utc.isoformat().replace("+00:00", "Z"),
        "total_downloads": all_time_total,
        "latest_release": latest.get("tag_name", ""),
        "latest_release_downloads": latest_total,
    }

    history_raw.append(snapshot)

    cutoff = now_utc - timedelta(days=MAX_HISTORY_DAYS)
    history_clean = []

    for point in valid_history(history_raw):
        if point["_timestamp"] >= cutoff:
            history_clean.append(point)

    deduped = {}
    for point in history_clean:
        deduped[point["timestamp"]] = point
    history_clean = sorted(deduped.values(), key=lambda p: p["_timestamp"])

    serializable_history = [
        {key: value for key, value in point.items() if not key.startswith("_")}
        for point in history_clean
    ]

    start_today_local = now_local.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    start_today_utc = start_today_local.astimezone(timezone.utc)

    downloads_today = delta_since(history_clean, all_time_total, start_today_utc)
    downloads_hour = delta_since(
        history_clean,
        all_time_total,
        now_utc - timedelta(hours=1),
    )
    downloads_week = delta_since(
        history_clean,
        all_time_total,
        now_utc - timedelta(days=7),
    )

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

    write_json(HISTORY_FILE, serializable_history)
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

    write_growth_graph(
        history_clean,
        now_utc,
        timedelta(hours=24),
        GRAPHS["24h"],
        "Download growth, last 24 hours",
    )
    write_growth_graph(
        history_clean,
        now_utc,
        timedelta(days=7),
        GRAPHS["7d"],
        "Download growth, last 7 days",
    )
    write_growth_graph(
        history_clean,
        now_utc,
        timedelta(days=30),
        GRAPHS["30d"],
        "Download growth, last 30 days",
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
