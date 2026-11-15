"""Collect candidate resources from GitHub, RSS feeds, blogs, HN, Reddit, arXiv.

Writes work/candidates.json (new, never-seen URLs only) and
work/candidates.md (human-readable digest). Nothing is added to the site
here — the reviewing agent decides, using the rubric in UPDATE_PLAYBOOK.md.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from common import (TZ, gh_json, github_repo, http_get, known_urls, load, norm_url,
                    save_work, today)

ATOM = "{http://www.w3.org/2005/Atom}"


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_date(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    try:
        return parsedate_to_datetime(s).date().isoformat()
    except (TypeError, ValueError):
        pass
    m = re.match(r"\d{4}-\d{2}-\d{2}", s)
    return m.group(0) if m else None


def matches(text: str, kws: list[str]) -> bool:
    t = text.lower()
    return any(re.search(r"(?<![a-z])" + re.escape(k.lower()) + r"(?![a-z])", t) for k in kws)


# ---------- sources ----------

def from_github(cfg: dict, since: str) -> list[dict]:
    out = []
    for q in cfg["queries"]:
        for flag in ("--created", "--updated"):
            time.sleep(2.2)  # search API: 30 requests/minute
            try:
                items = gh_json(["search", "repos", q, flag, f">={since}",
                                 "--stars", f">={cfg['min_stars']}", "--sort", "stars", "--limit", "15",
                                 "--json", "fullName,stargazersCount,description,createdAt,pushedAt,url"])
            except RuntimeError as e:
                print(f"[github] {q}: {e}", file=sys.stderr)
                continue
            for it in items or []:
                if it["stargazersCount"] < cfg["min_stars"]:
                    continue
                out.append({"url": it["url"], "title": it["fullName"], "source": f"GitHub 搜索：{q}",
                            "date": it["createdAt"][:10], "snippet": it.get("description") or "",
                            "stars": it["stargazersCount"], "pushed_at": it["pushedAt"][:10],
                            "new_repo": it["createdAt"][:10] >= since, "type_hint": "community"})
    return out


def from_feed(feed: dict, kws: list[str], since: str) -> list[dict]:
    code, _, body = http_get(feed["url"])
    if code != 200 or not body:
        print(f"[feed] {feed['name']}: HTTP {code}", file=sys.stderr)
        return []
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"[feed] {feed['name']}: {e}", file=sys.stderr)
        return []
    out = []
    items = root.iter("item") if root.find(".//item") is not None else root.iter(f"{ATOM}entry")
    for it in items:
        if it.tag == "item":
            title = it.findtext("title") or ""
            link = (it.findtext("link") or "").strip()
            date = parse_date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date"))
            summ = it.findtext("description") or ""
        else:
            title = it.findtext(f"{ATOM}title") or ""
            link_el = it.find(f"{ATOM}link[@rel='alternate']")
            if link_el is None:
                link_el = it.find(f"{ATOM}link")
            link = link_el.get("href") if link_el is not None else ""
            date = parse_date(it.findtext(f"{ATOM}published") or it.findtext(f"{ATOM}updated"))
            summ = it.findtext(f"{ATOM}summary") or it.findtext(f"{ATOM}content") or ""
        title, summ = strip_tags(title), strip_tags(summ)[:400]
        if not link or (date and date < since):
            continue
        if "reddit.com" in feed["url"]:
            # Reddit posts: keep the external link if the post shares one
            ext = re.findall(r'href="(https?://(?!www\.reddit|i\.redd|v\.redd|preview\.redd)[^"]+)"',
                             it.findtext(f"{ATOM}content") or "")
            if not ext:
                continue  # self-posts are discussions, not resources
            link = html.unescape(ext[0])
        if not matches(f"{title} {summ}", kws):
            continue
        out.append({"url": link, "title": title, "source": feed["name"], "date": date,
                    "snippet": summ, "type_hint": feed["type"]})
    return out


def from_page(page: dict, kws: list[str]) -> list[dict]:
    """Blogs without RSS: list same-site article links from the index page."""
    code, final, body = http_get(page["url"])
    if code != 200:
        print(f"[page] {page['name']}: HTTP {code}", file=sys.stderr)
        return []
    text = body.decode("utf-8", "replace")
    base = urllib.parse.urlsplit(final)
    seen, out = set(), []
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', text, re.S):
        href, inner = m.group(1), strip_tags(m.group(2))
        url = urllib.parse.urljoin(final, href)
        u = urllib.parse.urlsplit(url)
        if u.netloc != base.netloc or not u.path.startswith(page["link_prefix"]):
            continue
        if u.path.rstrip("/") in (base.path.rstrip("/"), page["link_prefix"].rstrip("/")) or len(inner) < 12:
            continue
        if url in seen:
            continue
        seen.add(url)
        # Index pages have no dates: keep only agent-related titles
        if not matches(inner, kws):
            continue
        out.append({"url": url, "title": inner[:160], "source": page["name"], "date": None,
                    "snippet": "", "type_hint": page["type"]})
    return out[:40]


def from_hn(cfg: dict, since_ts: int, kws: list[str]) -> list[dict]:
    out = []
    for q in cfg["queries"]:
        params = urllib.parse.urlencode({"query": q, "tags": "story",
                                         "numericFilters": f"points>{cfg['min_points']},created_at_i>{since_ts}",
                                         "hitsPerPage": 50})
        code, _, body = http_get(f"https://hn.algolia.com/api/v1/search?{params}")
        if code != 200:
            print(f"[hn] {q}: HTTP {code}", file=sys.stderr)
            continue
        for h in json.loads(body).get("hits", []):
            if not h.get("url") or not matches(h.get("title") or "", kws):
                continue
            out.append({"url": h["url"], "title": h.get("title") or "", "source": f"Hacker News（{h.get('points')} 分）",
                        "date": (h.get("created_at") or "")[:10], "snippet": f"HN 讨论：https://news.ycombinator.com/item?id={h['objectID']}",
                        "points": h.get("points"), "type_hint": "community"})
    return out


def from_arxiv(cfg: dict, since: str) -> list[dict]:
    params = urllib.parse.urlencode({"search_query": cfg["query"], "sortBy": "submittedDate",
                                     "sortOrder": "descending", "max_results": cfg["max_results"]})
    code, _, body = http_get(f"http://export.arxiv.org/api/query?{params}", timeout=40)
    if code != 200:
        print(f"[arxiv] HTTP {code}", file=sys.stderr)
        return []
    out = []
    for e in ET.fromstring(body).iter(f"{ATOM}entry"):
        date = (e.findtext(f"{ATOM}published") or "")[:10]
        if date < since:
            continue
        link = (e.findtext(f"{ATOM}id") or "").replace("http://", "https://")
        link = re.sub(r"v\d+$", "", link)
        out.append({"url": link, "title": strip_tags(e.findtext(f"{ATOM}title") or ""), "source": "arXiv",
                    "date": date, "snippet": strip_tags(e.findtext(f"{ATOM}summary") or "")[:400],
                    "type_hint": "academic"})
    return out


# ---------- main ----------

def main() -> int:
    cfg = load("sources.json")
    data = load("resources.json")
    reviewed = load("reviewed.json", {})
    seen = known_urls(data["resources"], reviewed)
    now = dt.datetime.now(TZ)
    since = (now - dt.timedelta(days=cfg["lookback_days"])).date().isoformat()
    since_ts = int((now - dt.timedelta(days=cfg["lookback_days"])).timestamp())
    kws = cfg["keywords"]

    jobs = []
    with cf.ThreadPoolExecutor(8) as ex:
        jobs.append(ex.submit(from_github, cfg["github"], since))
        jobs += [ex.submit(from_feed, f, kws, since) for f in cfg["feeds"]]
        jobs += [ex.submit(from_page, p, kws) for p in cfg["pages"]]
        jobs.append(ex.submit(from_hn, cfg["hackernews"], since_ts, kws))
        jobs.append(ex.submit(from_arxiv, cfg["arxiv"], since))
        raw = [c for j in jobs for c in j.result()]

    cands: dict[str, dict] = {}
    for c in raw:
        repo = github_repo(c["url"])
        if repo:
            c["url"] = f"https://github.com/{repo}"
            c["github"] = repo
        key = norm_url(c["url"])
        if key in seen:
            continue
        if key in cands:
            cands[key]["source"] += f"；{c['source']}"
            continue
        c["key"] = key
        cands[key] = c

    ordered = sorted(cands.values(), key=lambda c: (c.get("date") or "", c.get("stars") or 0), reverse=True)
    save_work("candidates.json", {"generated": today(), "since": since, "count": len(ordered), "items": ordered})

    lines = [f"# 候选资料 {today()}（{since} 以来，{len(ordered)} 条未收录）", ""]
    by_src: dict[str, list] = {}
    for c in ordered:
        by_src.setdefault(c["source"].split("：")[0].split("（")[0], []).append(c)
    for src, items in sorted(by_src.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"## {src}（{len(items)}）")
        for c in items:
            meta = " · ".join(x for x in [c.get("date") or "", f"{c['stars']}★" if c.get("stars") else "",
                                          c["source"]] if x)
            lines.append(f"- [{c['title']}]({c['url']}) — {meta}")
            if c.get("snippet"):
                lines.append(f"  > {c['snippet'][:220]}")
        lines.append("")
    p = save_work("candidates.md", "\n".join(lines))
    print(f"{len(raw)} raw → {len(ordered)} new candidates → {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
