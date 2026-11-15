"""Look up URLs against the library before reviewing them (stdlib + optional gh).

Usage: python3 scripts/lookup.py URL [URL ...]

For each URL prints whether it is already in data/resources.json (main url,
extra_links or github repo), already in data/reviewed.json, known aliases of the
same article, similar titles, and live GitHub stats for repos.
"""
from __future__ import annotations

import re
import sys

from common import gh_json, github_repo, load, norm_url

# Same article published under several paths.
ALIASES = [
    (re.compile(r"^anthropic\.com/engineering/"), "anthropic.com/research/"),
    (re.compile(r"^anthropic\.com/research/"), "anthropic.com/engineering/"),
    (re.compile(r"^docs\.anthropic\.com/en/docs/claude-code/"), "code.claude.com/docs/en/"),
]


def variants(url: str) -> set[str]:
    n = norm_url(url)
    out = {n}
    for pat, repl in ALIASES:
        if pat.match(n):
            out.add(pat.sub(repl, n))
    return out


def words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}|[一-鿿]{2,}", s.lower())}


def main(urls: list[str]) -> int:
    if not urls:
        print(__doc__)
        return 1
    data = load("resources.json")
    res = data["resources"]
    reviewed = load("reviewed.json", {})
    index: dict[str, tuple[str, str]] = {}
    for r in res:
        index[norm_url(r["url"])] = (r["id"], "url")
        for x in r.get("extra_links", []):
            index.setdefault(norm_url(x["url"]), (r["id"], f"extra_links:{x.get('label', '')}"))
        if r.get("github"):
            index.setdefault(norm_url(f"https://github.com/{r['github']}"), (r["id"], "github"))
    by_id = {r["id"]: r for r in res}

    for url in urls:
        print(f"== {url}")
        hit = False
        for v in variants(url):
            if v in index:
                rid, where = index[v]
                r = by_id[rid]
                print(f"  已收录: {rid} ({where}) score={r.get('score')} category={r['category']} — {r['title']}")
                hit = True
            if v in reviewed:
                x = reviewed[v]
                print(f"  已审核: {x.get('date')} {x.get('decision')} score={x.get('score')} — {x.get('reason')}")
                hit = True
        if not hit:
            print("  未收录、未审核")
        repo = github_repo(url)
        if repo:
            try:
                g = gh_json(["api", f"repos/{repo}"])
                print(f"  GitHub: {g['full_name']} ★{g['stargazers_count']} pushed={g['pushed_at'][:10]}"
                      f" archived={g['archived']} license={(g.get('license') or {}).get('spdx_id')}")
                print(f"  描述: {g.get('description')}")
                key = words(repo.replace("/", " ").replace("-", " ") + " " + (g.get("description") or ""))
            except Exception as ex:  # noqa: BLE001
                print(f"  GitHub 查询失败: {ex}")
                key = words(repo.replace("-", " "))
        else:
            key = words(re.sub(r"[/_.-]", " ", norm_url(url).split("/", 1)[-1]))
        sims = []
        for r in res:
            overlap = key & words(r["title"] + " " + r.get("desc", ""))
            if len(overlap) >= 2:
                sims.append((len(overlap), r))
        for _, r in sorted(sims, key=lambda t: -t[0])[:5]:
            print(f"  相近条目: {r['id']} [{r['category']}] {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
