"""Health check: refresh GitHub stats and verify every link.

Updates data/resources.json in place (stars, pushed_at, status, fail_count,
last_checked) and writes work/check-report.md for the human/agent reviewer.

A link is only marked `broken` after 2 consecutive failed checks, so one
flaky run never removes anything.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import sys
import urllib.parse

from common import TZ, gh_json, http_get, load, save, save_work, today

STALE_DAYS = 365


def check_repo(repo: str) -> dict:
    try:
        d = gh_json(["api", f"repos/{repo}"])
    except RuntimeError as e:
        return {"error": str(e)[:200]}
    return {"stars": d["stargazers_count"], "pushed_at": d["pushed_at"][:10],
            "archived": d["archived"], "full_name": d["full_name"],
            "description": d.get("description") or ""}


def check_url(url: str) -> tuple[int, str]:
    status, final, _ = http_get(url, timeout=25, method="GET")
    return status, final


def moved(u: str, final: str) -> bool:
    """True if a redirect points to a different article, not just a site root tweak."""
    a, b = urllib.parse.urlsplit(u), urllib.parse.urlsplit(final)
    if a.path.strip("/") == "":  # homepage redirects (www, versioned docs) are fine
        return a.netloc.removeprefix("www.") != b.netloc.removeprefix("www.")
    return (a.netloc.removeprefix("www."), a.path.rstrip("/")) != (b.netloc.removeprefix("www."), b.path.rstrip("/"))


def main() -> int:
    data = load("resources.json")
    res = data["resources"]
    now = dt.datetime.now(TZ).date()
    lines = [f"# 健康检查报告 {today()}", ""]
    problems, renamed, stale = [], [], []

    with cf.ThreadPoolExecutor(8) as ex:
        repo_jobs = {ex.submit(check_repo, r["github"]): r for r in res if r.get("github")}
        url_jobs = {}
        for r in res:
            urls = [r["url"]] if not r.get("github") or "github.com" not in r["url"] else []
            urls += [x["url"] for x in r.get("extra_links", []) if "github.com" not in x["url"]]
            for u in urls:
                url_jobs[ex.submit(check_url, u)] = (r, u)

        repo_info = {}
        for f in cf.as_completed(repo_jobs):
            repo_info[repo_jobs[f]["id"]] = f.result()
        url_info: dict[str, list] = {}
        for f in cf.as_completed(url_jobs):
            r, u = url_jobs[f]
            url_info.setdefault(r["id"], []).append((u, *f.result()))

    for r in res:
        failed = False
        status = "ok"
        info = repo_info.get(r["id"])
        if info is not None:
            if "error" in info:
                failed = True
                problems.append(f"- `{r['id']}` GitHub API 失败：{info['error']}")
            else:
                r["stars"], r["pushed_at"] = info["stars"], info["pushed_at"]
                if info["full_name"].lower() != r["github"].lower():
                    renamed.append(f"- `{r['id']}` 仓库已改名/转移：{r['github']} → {info['full_name']}")
                if info["archived"]:
                    status = "archived"
                elif (not r.get("evergreen")
                      and (now - dt.date.fromisoformat(info["pushed_at"])).days > STALE_DAYS):
                    status = "stale"
                    stale.append(f"- `{r['id']}` 最近推送 {info['pushed_at']}")
        for u, code, final in url_info.get(r["id"], []):
            # 403/429 usually means bot protection, not a dead page
            if code in (0, 404, 410) or code >= 500:
                failed = True
                problems.append(f"- `{r['id']}` {u} → HTTP {code or '网络错误'}")
            elif moved(u, final) and status == "ok":
                status = "redirect"
                renamed.append(f"- `{r['id']}` 重定向：{u} → {final}")
        r["fail_count"] = r.get("fail_count", 0) + 1 if failed else 0
        if r["fail_count"] >= 2:
            status = "broken"
        r["status"] = status
        r["last_checked"] = today()

    save("resources.json", data)
    broken = [r for r in res if r["status"] == "broken"]
    lines += [f"共检查 {len(res)} 条；连续 2 次失败（broken）{len(broken)} 条；"
              f"本次失败 {len(problems)} 处；久未更新 {len(stale)} 条。", ""]
    for title, items in [("## 本次失败", problems), ("## 改名 / 重定向", renamed),
                         ("## 超过一年未更新", stale),
                         ("## 已判定失效（需处理）", [f"- `{r['id']}` {r['url']}" for r in broken])]:
        lines += [title, *(items or ["- 无"]), ""]
    p = save_work("check-report.md", "\n".join(lines))
    print(p.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
