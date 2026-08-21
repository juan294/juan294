#!/usr/bin/env python3
"""Render the profile terminal SVG with current public GitHub statistics."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
USERNAME = "juan294"
API = "https://api.github.com"


def github_json(url: str, token: str, data: dict | None = None) -> dict | list:
    body = None if data is None else json.dumps(data).encode()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def collect_stats() -> dict[str, int]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    user = github_json(f"{API}/users/{USERNAME}", token)
    repos = github_json(
        f"{API}/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated", token
    )
    return {
        "repos": int(user["public_repos"]),
        "stars": sum(int(repo["stargazers_count"]) for repo in repos),
        "followers": int(user["followers"]),
    }


def text(x: int, y: int, value: str, class_name: str) -> str:
    return f'<text x="{x}" y="{y}" class="{class_name}">{escape(value)}</text>'


def row(y: int, label: str, value: str) -> list[str]:
    return [
        f'<line x1="625" y1="{y - 4}" x2="1138" y2="{y - 4}" class="leader"/>',
        text(480, y, label, "label"),
        text(740, y, value, "value"),
    ]


def render(stats: dict[str, int]) -> str:
    portrait = (ROOT / "assets" / "portrait.txt").read_text().splitlines()
    elements: list[str] = []

    for index, line in enumerate(portrait):
        elements.append(text(40, 105 + index * 14, line, "portrait"))

    elements.extend(
        [
            text(480, 91, "juan294@github", "identity"),
            '<line x1="650" y1="84" x2="1148" y2="84" class="rule"/>',
        ]
    )

    y = 124
    for label, value in [
        ("OS", "macOS / Linux"),
        ("Shell", "zsh"),
        ("Host", "Avolta + independent builds"),
        ("Role", "Digital Architect / Developer / Entrepreneur"),
        ("Previous", "Amazon Alexa / health-tech founder"),
    ]:
        elements.extend(row(y, label, value))
        y += 25

    y += 13
    for label, value in [
        ("Languages.Code", "TypeScript, Python, JavaScript, Shell"),
        ("Languages.Real", "English, Spanish"),
        ("Focus", "production AI agents + developer tools"),
        ("Method", "RPI / TDD / CI/CD"),
    ]:
        elements.extend(row(y, label, value))
        y += 25

    y += 13
    elements.extend(
        [
            text(480, y, "- Contact", "section"),
            f'<line x1="590" y1="{y - 6}" x2="1148" y2="{y - 6}" class="rule"/>',
        ]
    )
    y += 31
    for label, value in [
        ("Email", "juan294@gmail.com"),
        ("Portfolio", "portfolio.thecreativetoken.com"),
        ("Medium", "medium.com/@juang294"),
        ("GitHub", "github.com/juan294"),
    ]:
        elements.extend(row(y, label, value))
        y += 25

    y += 13
    elements.extend(
        [
            text(480, y, "- GitHub Stats", "section"),
            f'<line x1="635" y1="{y - 6}" x2="1148" y2="{y - 6}" class="rule"/>',
        ]
    )
    y += 31
    elements.extend(row(y, "Public repos", f'{stats["repos"]:,}'))
    elements.extend(row(y + 25, "Stars", f'{stats["stars"]:,}'))
    elements.extend(row(y + 50, "Followers", f'{stats["followers"]:,}'))

    body = "\n    ".join(elements)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="650" viewBox="0 0 1200 650" role="img" aria-labelledby="title desc">
  <title id="title">Juan Gonzalez terminal profile</title>
  <desc id="desc">An ASCII portrait of Juan Gonzalez beside professional details, contact links, and current GitHub statistics.</desc>
  <defs>
    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0a1018"/>
      <stop offset="0.55" stop-color="#101923"/>
      <stop offset="1" stop-color="#0a111b"/>
    </linearGradient>
    <linearGradient id="portraitInk" x1="0" y1="0" x2="0.9" y2="1">
      <stop offset="0" stop-color="#d6e7f7"/>
      <stop offset="0.5" stop-color="#79c0ff"/>
      <stop offset="1" stop-color="#f0a65b"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="12" stdDeviation="18" flood-color="#000" flood-opacity="0.38"/>
    </filter>
  </defs>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    .portrait {{ font-size: 12px; white-space: pre; fill: url(#portraitInk); letter-spacing: 0.15px; }}
    .chrome {{ font-size: 15px; font-weight: 600; fill: #8b949e; }}
    .identity {{ font-size: 20px; font-weight: 700; fill: #e6edf3; }}
    .label {{ font-size: 16px; font-weight: 700; fill: #f0a65b; paint-order: stroke; stroke: #0e1721; stroke-width: 6px; }}
    .value {{ font-size: 16px; fill: #9ecbff; paint-order: stroke; stroke: #0e1721; stroke-width: 6px; }}
    .section {{ font-size: 17px; font-weight: 700; fill: #d9e2ec; paint-order: stroke; stroke: #0e1721; stroke-width: 6px; }}
    .leader {{ stroke: #35404d; stroke-width: 1.2; stroke-dasharray: 1 7; }}
    .rule {{ stroke: #46515f; stroke-width: 1.4; }}
  </style>
  <rect x="12" y="12" width="1176" height="626" rx="20" fill="url(#background)" stroke="#303b49" stroke-width="2" filter="url(#shadow)"/>
  <rect x="12" y="12" width="1176" height="52" rx="20" fill="#151f2b"/>
  <path d="M12 44v20h1176V44" fill="#151f2b"/>
  <circle cx="38" cy="38" r="7" fill="#ff7b72"/>
  <circle cx="62" cy="38" r="7" fill="#f2cc60"/>
  <circle cx="86" cy="38" r="7" fill="#56d364"/>
  {text(112, 44, "juan294 / README.md", "chrome")}
  <line x1="448" y1="84" x2="448" y2="608" stroke="#2a3542" stroke-width="1.5"/>
  {body}
</svg>
'''


def main() -> None:
    stats = collect_stats()
    destination = ROOT / "assets" / "terminal.svg"
    destination.write_text(render(stats))
    print(
        "Rendered terminal.svg: "
        f'{stats["repos"]} repos, {stats["stars"]} stars, '
        f'{stats["followers"]} followers'
    )


if __name__ == "__main__":
    main()
