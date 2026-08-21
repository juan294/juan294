#!/usr/bin/env python3
"""Render theme-aware profile SVGs with current public GitHub statistics."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
USERNAME = "juan294"
API = "https://api.github.com"
ROW_WIDTH = 54
PORTRAIT_COLUMNS = 40
PORTRAIT_ROWS = 20


THEMES = {
    "dark_mode.svg": {
        "background": "#161b22",
        "text": "#c9d1d9",
        "key": "#ffa657",
        "value": "#a5d6ff",
        "leader": "#616e7f",
    },
    "light_mode.svg": {
        "background": "#f6f8fa",
        "text": "#24292f",
        "key": "#953800",
        "value": "#0550ae",
        "leader": "#6e7781",
    },
}


def github_json(url: str, token: str) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def collect_stats() -> dict[str, int]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    user = github_json(f"{API}/users/{USERNAME}", token)
    if not isinstance(user, dict):
        raise TypeError("GitHub user response must be an object")

    repos: list[dict] = []
    page = 1
    while True:
        batch = github_json(
            f"{API}/users/{USERNAME}/repos"
            f"?per_page=100&type=owner&sort=updated&page={page}",
            token,
        )
        if not isinstance(batch, list):
            raise TypeError("GitHub repositories response must be a list")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return {
        "repos": int(user["public_repos"]),
        "stars": sum(int(repo["stargazers_count"]) for repo in repos),
        "followers": int(user["followers"]),
    }


def markup_line(y: int, markup: str, x: int = 410) -> str:
    return f'<tspan x="{x}" y="{y}">{markup}</tspan>'


def text_line(y: int, value: str, x: int = 410) -> str:
    return markup_line(y, escape(value), x)


def row(y: int, label: str, value: str) -> str:
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
        f'<tspan class="value">{escape(value)}</tspan>',
    )


def section(y: int, title: str) -> str:
    rule = "—" * max(1, ROW_WIDTH - len(title) - 3)
    return text_line(y, f"- {title} {rule}")


def build_content(stats: dict[str, int], portrait: list[str]) -> tuple[str, str]:
    portrait_lines = "\n".join(
        f'    <tspan x="15" y="{70 + index * 20}">{escape(value)}</tspan>'
        for index, value in enumerate(portrait)
    )

    details = [
        text_line(30, "juan@github " + "—" * 41),
        row(50, "OS", "macOS, Linux"),
        row(70, "Host", "Avolta"),
        row(90, "Role", "Digital Architect / Developer"),
        row(110, "Prev", "Amazon Alexa / health-tech founder"),
        row(130, "Tools", "Codex, Claude Code, Ghostty"),
        markup_line(150, '<tspan class="cc">. </tspan>'),
        row(170, "Languages.Programming", "TypeScript, Python, JS"),
        row(190, "Languages.Platform", "Next.js, React, Node.js, SQL"),
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
        markup_line(
            470,
            '<tspan class="cc">. </tspan>'
            '<tspan class="key">Repos</tspan>: '
            f'<tspan class="value">{stats["repos"]:,}</tspan> | '
            '<tspan class="key">Stars</tspan>: '
            f'<tspan class="value">{stats["stars"]:,}</tspan> | '
            '<tspan class="key">Followers</tspan>: '
            f'<tspan class="value">{stats["followers"]:,}</tspan>',
        ),
        row(490, "Method", "RPI / TDD / CI/CD"),
        row(510, "Location", "Gijón, Asturias, Spain"),
    ]
    detail_lines = "\n    ".join(details)
    return portrait_lines, detail_lines


def render(colors: dict[str, str], portrait_lines: str, detail_lines: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,monospace" viewBox="0 0 985 530" width="985px" height="530px" font-size="16px" role="img" aria-labelledby="title desc">
  <title id="title">Juan Gonzalez terminal profile</title>
  <desc id="desc">An ASCII portrait beside professional details, contact links, and public GitHub statistics.</desc>
  <style>
    .key {{ fill: {colors["key"]}; }}
    .value {{ fill: {colors["value"]}; }}
    .cc {{ fill: {colors["leader"]}; }}
    text, tspan {{ white-space: pre; }}
  </style>
  <rect width="985" height="530" fill="{colors["background"]}" rx="15"/>
  <text fill="{colors["text"]}" class="ascii">
{portrait_lines}
  </text>
  <text fill="{colors["text"]}">
    {detail_lines}
  </text>
</svg>
'''


def main() -> None:
    stats = collect_stats()
    portrait = (ROOT / "assets" / "portrait.txt").read_text(encoding="utf-8").splitlines()
    if len(portrait) != PORTRAIT_ROWS or any(
        len(line) > PORTRAIT_COLUMNS for line in portrait
    ):
        raise ValueError(
            f"Portrait must be {PORTRAIT_ROWS} rows and at most "
            f"{PORTRAIT_COLUMNS} columns"
        )
    portrait_lines, detail_lines = build_content(stats, portrait)
    for filename, colors in THEMES.items():
        (ROOT / filename).write_text(
            render(colors, portrait_lines, detail_lines), encoding="utf-8"
        )
    print(
        f'Rendered {" and ".join(THEMES)}: '
        f'{stats["repos"]} repos, {stats["stars"]} stars, '
        f'{stats["followers"]} followers'
    )


if __name__ == "__main__":
    main()
