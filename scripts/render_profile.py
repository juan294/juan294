#!/usr/bin/env python3
"""Render theme-aware profile SVGs with current GitHub statistics."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "juan294"
API = "https://api.github.com"
PORTFOLIO_API = "https://portfolio.thecreativetoken.com/api/activity"
ROW_WIDTH = 54
ART_COLUMNS = 54
ART_ROWS = 36
ACTIVITY_PERIOD = "12mo"


THEMES = {
    "dark_mode.svg": {
        "background": "#161b22",
        "text": "#c9d1d9",
        "key": "#ffa657",
        "value": "#a5d6ff",
        "leader": "#616e7f",
        "positive": "#3fb950",
        "negative": "#f85149",
    },
    "light_mode.svg": {
        "background": "#f6f8fa",
        "text": "#24292f",
        "key": "#953800",
        "value": "#0550ae",
        "leader": "#6e7781",
        "positive": "#1a7f37",
        "negative": "#cf222e",
    },
}


class ProfileStats(TypedDict):
    repos: int
    stars: int
    followers: int
    commits: int
    prs: int
    issue_resolution_rate: int
    lines_added: int
    lines_deleted: int
    net_lines: int


class ActivityStats(TypedDict):
    commits: int
    prs: int
    issue_resolution_rate: int
    lines_added: int
    lines_deleted: int


def fetch_json(url: str, headers: dict[str, str]) -> dict | list:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def github_json(url: str, token: str) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return fetch_json(url, headers)


def portfolio_month_stats(period: tuple[int, int]) -> ActivityStats:
    year, month = period
    activity = fetch_json(
        f"{PORTFOLIO_API}?range=days&month={month}&year={year}",
        {
            "Accept": "application/json",
            "User-Agent": f"{USERNAME}-profile-readme",
        },
    )
    if not isinstance(activity, dict) or not isinstance(activity.get("stats"), dict):
        raise TypeError("Portfolio activity response must contain a stats object")

    activity_stats = activity["stats"]
    try:
        return {
            "commits": int(activity_stats["commits"]),
            "prs": int(activity["prCount"]),
            "issue_resolution_rate": int(activity["issueResolutionRate"]),
            "lines_added": int(activity_stats["linesAdded"]),
            "lines_deleted": int(activity_stats["linesDeleted"]),
        }
    except (KeyError, TypeError, ValueError) as error:
        raise TypeError("Portfolio activity response has invalid metrics") from error


def trailing_twelve_months(now: datetime) -> list[tuple[int, int]]:
    current_month = now.year * 12 + now.month - 1
    periods = []
    for offset in range(11, -1, -1):
        year, zero_based_month = divmod(current_month - offset, 12)
        periods.append((year, zero_based_month + 1))
    return periods


def shift_month(now: datetime, months_back: int) -> datetime:
    if months_back not in (0, 1):
        raise ValueError("ACTIVITY_MONTH_OFFSET must be 0 or 1")
    month_index = now.year * 12 + now.month - 1 - months_back
    year, zero_based_month = divmod(month_index, 12)
    return now.replace(year=year, month=zero_based_month + 1, day=1)


def collect_activity_stats(now: datetime) -> ActivityStats:
    periods = trailing_twelve_months(now)
    with ThreadPoolExecutor(max_workers=4) as executor:
        months = list(executor.map(portfolio_month_stats, periods))

    return {
        "commits": sum(month["commits"] for month in months),
        "prs": sum(month["prs"] for month in months),
        "issue_resolution_rate": months[-1]["issue_resolution_rate"],
        "lines_added": sum(month["lines_added"] for month in months),
        "lines_deleted": sum(month["lines_deleted"] for month in months),
    }


def collect_stats() -> ProfileStats:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    user = github_json(f"{API}/users/{USERNAME}", token)
    if not isinstance(user, dict):
        raise TypeError("GitHub user response must be an object")

    # /user/repos (authenticated) includes private repos, unlike
    # /users/{username}/repos which is always public-only regardless of
    # the caller's credentials. Requires a token with repo scope (see
    # PROFILE_PAT in the workflow) rather than the default GITHUB_TOKEN.
    repos: list[dict] = []
    page = 1
    while True:
        batch = github_json(
            f"{API}/user/repos"
            f"?per_page=100&type=owner&sort=updated&page={page}",
            token,
        )
        if not isinstance(batch, list):
            raise TypeError("GitHub repositories response must be a list")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    month_offset = int(os.environ.get("ACTIVITY_MONTH_OFFSET", "0"))
    activity_month = shift_month(datetime.now(timezone.utc), month_offset)
    activity = collect_activity_stats(activity_month)
    lines_added = activity["lines_added"]
    lines_deleted = activity["lines_deleted"]
    return {
        "repos": len(repos),
        "stars": sum(int(repo["stargazers_count"]) for repo in repos),
        "followers": int(user["followers"]),
        "commits": activity["commits"],
        "prs": activity["prs"],
        "issue_resolution_rate": activity["issue_resolution_rate"],
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "net_lines": lines_added - lines_deleted,
    }


def markup_line(y: int, markup: str, x: int = 410) -> str:
    return f'<tspan x="{x}" y="{y}">{markup}</tspan>'


def text_line(y: int, value: str, x: int = 410) -> str:
    return markup_line(y, escape(value), x)


def aligned_markup_row(y: int, label: str, value: str, value_markup: str) -> str:
    fixed_width = 2 + len(label) + 1 + 1 + 1 + len(value)
    dot_count = ROW_WIDTH - fixed_width
    if dot_count < 1:
        raise ValueError(f"Profile row exceeds {ROW_WIDTH} columns: {label}: {value}")
    dots = "." * dot_count
    return markup_line(
        y,
        '<tspan class="cc">. </tspan>'
        f'<tspan class="key">{escape(label)}</tspan>:'
        f'<tspan class="cc"> {dots} </tspan>'
        f"{value_markup}",
    )


def row(y: int, label: str, value: str) -> str:
    return aligned_markup_row(
        y,
        label,
        value,
        f'<tspan class="value">{escape(value)}</tspan>',
    )


def section(y: int, title: str) -> str:
    rule = "—" * max(1, ROW_WIDTH - len(title) - 3)
    return text_line(y, f"- {title} {rule}")


def build_content(stats: ProfileStats, art: list[str]) -> tuple[str, str]:
    art_lines = "\n".join(
        f'    <tspan x="8" y="{13 + index * 14}">{escape(value)}</tspan>'
        for index, value in enumerate(art)
    )

    details = [
        text_line(30, "juan@github " + "—" * 41),
        row(50, "OS", "macOS, Linux"),
        row(70, "Host", "Avolta"),
        row(90, "Role", "Digital Architect / Developer"),
        row(110, "Prev", "Amazon Alexa / health-tech founder"),
        row(130, "Tools", "Codex, Claude Code, Ghostty"),
        row(150, "Built", "Summon, GH-Glance"),
        row(170, "Building.With", "TypeScript, Python, JavaScript"),
        row(190, "Building.On", "Next.js, React, Node.js, SQL"),
        row(210, "Languages.Real", "English, Spanish"),
        markup_line(230, '<tspan class="cc">. </tspan>'),
        row(250, "Focus", "production AI agents + developer tools"),
        row(270, "Shipped", "voice products + terminal tooling"),
        section(310, "Contact"),
        row(330, "Email", "juan294@gmail.com"),
        row(350, "Web", "portfolio.thecreativetoken.com"),
        row(370, "Twitter", "@JuanG294"),
        row(390, "LinkedIn", "juanagonzalezp"),
        row(410, "Medium", "@juang294"),
        section(450, "GitHub Stats"),
        aligned_markup_row(
            470,
            "Repos",
            f"{stats['repos']:,} | Stars {stats['stars']:,} | Followers {stats['followers']:,}",
            f'<tspan class="value">{stats["repos"]:,}</tspan> | '
            '<tspan class="key">Stars</tspan> '
            f'<tspan class="value">{stats["stars"]:,}</tspan> | '
            '<tspan class="key">Followers</tspan> '
            f'<tspan class="value">{stats["followers"]:,}</tspan>',
        ),
        aligned_markup_row(
            490,
            f"Commits.{ACTIVITY_PERIOD}",
            f"{stats['commits']:,} | PRs {stats['prs']:,} | "
            f"Resolved {stats['issue_resolution_rate']}%",
            f'<tspan class="value">{stats["commits"]:,}</tspan> | '
            '<tspan class="key">PRs</tspan> '
            f'<tspan class="value">{stats["prs"]:,}</tspan> | '
            '<tspan class="key">Resolved</tspan> '
            f'<tspan class="value">{stats["issue_resolution_rate"]}%</tspan>',
        ),
        aligned_markup_row(
            510,
            f"NetLOC.{ACTIVITY_PERIOD}",
            f"{stats['net_lines']:,} (+{stats['lines_added']:,}, "
            f"-{stats['lines_deleted']:,})",
            f'<tspan class="value">{stats["net_lines"]:,}</tspan> ('
            f'<tspan class="positive">+{stats["lines_added"]:,}</tspan>, '
            f'<tspan class="negative">-{stats["lines_deleted"]:,}</tspan>)',
        ),
    ]
    detail_lines = "\n    ".join(details)
    return art_lines, detail_lines


def render(colors: dict[str, str], art_lines: str, detail_lines: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,monospace" viewBox="0 0 985 530" width="985px" height="530px" font-size="16px" role="img" aria-labelledby="title desc">
  <title id="title">Juan Gonzalez terminal profile</title>
  <desc id="desc">An ASCII walking traveler beside professional details, contact links, and GitHub statistics.</desc>
  <style>
    .key {{ fill: {colors["key"]}; }}
    .value {{ fill: {colors["value"]}; }}
    .cc {{ fill: {colors["leader"]}; }}
    .positive {{ fill: {colors["positive"]}; }}
    .negative {{ fill: {colors["negative"]}; }}
    text, tspan {{ white-space: pre; }}
  </style>
  <rect width="985" height="530" fill="{colors["background"]}" rx="15"/>
  <text fill="{colors["text"]}" class="ascii" font-size="12px">
{art_lines}
  </text>
  <text fill="{colors["text"]}">
    {detail_lines}
  </text>
</svg>
'''


def main() -> None:
    stats = collect_stats()
    art = (ROOT / "assets" / "wanderer.txt").read_text(encoding="utf-8").splitlines()
    if len(art) != ART_ROWS or any(len(line) > ART_COLUMNS for line in art):
        raise ValueError(
            f"ASCII art must be {ART_ROWS} rows and at most {ART_COLUMNS} columns"
        )
    art_lines, detail_lines = build_content(stats, art)
    for filename, colors in THEMES.items():
        (ROOT / filename).write_text(
            render(colors, art_lines, detail_lines), encoding="utf-8"
        )
    print(
        f"Rendered {' and '.join(THEMES)}: "
        f"{stats['repos']} repos, {stats['stars']} stars, "
        f"{stats['followers']} followers, {stats['commits']} commits, "
        f"{stats['lines_added']} additions, {stats['lines_deleted']} deletions"
    )


if __name__ == "__main__":
    main()
