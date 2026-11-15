# 每周更新手册（给执行更新的 agent）

目标：让网站保持**高质量 + 新鲜**。宁缺毋滥：一周没有够格的新资料，就只发布健康检查结果，不凑数。

工作目录：本仓库根目录。所有脚本只用 Python 标准库 + `gh` CLI。

## 流程

1. **同步**：`git pull --ff-only`。失败（有冲突/本地脏）就停止，报告原因，不要强推。
2. **健康检查**：`python3 scripts/check.py` → 读 `work/check-report.md`。
   - `改名 / 重定向`：把 `data/resources.json` 和 `content/` 下各页面里的旧 URL 换成新 URL（确认新地址是同一内容，不是首页或登录页）。
   - `已判定失效`：先手动 `curl -IL` 复核；确实失效就把该条移出 `resources.json`，在 changelog 的 `removed` 记录 `{id,title,reason}`；如果它在教程正文被引用，找替代并改对应的 `content/` 页面。
   - `超过一年未更新`：评估是否仍有价值。经典/规范类（DDIA 精读、凤凰架构、C4 model）设 `"evergreen": true`；过时的移除或降级说明。
3. **搜集候选**：`python3 scripts/discover.py` → 读 `work/candidates.md`（已排除收录过和审核过的 URL）。
4. **补充检索（必须做，不能只靠脚本）**：用 Web 搜索查最近 3 周的
   - 架构经典：Martin Fowler Blog、O'Reilly Radar、InfoQ Architecture 新发布的架构文章；
   - 中文技术博客：美团/字节/阿里/腾讯技术团队的架构实践文章；
   - 分布式系统：VLDB/OSDI/SOSP 新发布的系统论文；
   - AI 架构：RAG 系统设计、Agent 编排架构、模型网关、向量数据库；
   - ADR 工具：adr-tools / Log4brains / adr-kit 新版本或新实践。
5. **审核**：对每个有希望的候选，**打开原文读**（README / 正文 / 目录），按下方评分标准打分。不要只看标题和 star 数。
6. **写入**：通过的条目加进 `data/resources.json`；所有看过的候选（通过和拒绝都算）写进 `data/reviewed.json`，避免下周重复审核。
7. **教程正文**：只有出现明显更好的资料或某阶段内容过时，才改教程页面。改动要在 changelog 的 `guide_changes` 里写清楚。主教材更换需要非常强的理由。页面对应关系：
   - 首页的"推荐主线"和"推荐组合"：`content/home.html`
   - 学习路线每个阶段的阅读清单：`content/phases/p0.html` … `p6.html`（只写 `<ul>` 列表）
   - 阶段标题、周次、一句话简介、产出：`content/phases.json`
   - 毕业项目、学习建议、评分标准：`content/about.html`
   - 资料库页面是自动生成的，不要手改，改 `data/resources.json`。
   - 每个阶段页保持 4–7 条阅读材料，新增时同步淘汰过时的，别越堆越长。
8. **更新日志**：在 `data/changelog.json` 最前面加一条（见格式）。
9. **构建与自检**：`python3 scripts/build.py`（会做数据校验，失败必须修好），再用浏览器或 `grep` 抽查 `docs/index.html`、`docs/resources.html`、`docs/changelog.html`。
10. **发布**：`git add -A && git commit -m "update: YYYY-MM-DD ..." && git push`。推送后约 1 分钟 GitHub Pages 生效，用 `curl -s https://hustlyt.github.io/architecture-guide/changelog.html | grep YYYY-MM-DD` 确认。
11. **汇报**：用中文简要说明新增几条（列标题）、移除/调整了什么、正文是否改动、网站链接。

## 质量评分标准（满分 10，**≥ 7 才收录**）

| 维度 | 分值 | 看什么 |
|---|---|---|
| 深度与系统性 | 0–3 | 讲清原理和"为什么"，有完整结构；单篇浅显介绍、营销软文 = 0 |
| 可实践性 | 0–2 | 有可运行代码、练习或真实案例；架构图 + ADR 示例比单纯概念好 |
| 来源可信度 | 0–2 | 官方 / 知名团队 / 有一手经验的作者 / 同行评审；匿名搬运 = 0 |
| 新颖性 | 0–2 | 覆盖资料库里还没有的主题，或明显比现有条目更好/更新 |
| 维护与口碑 | 0–1 | 近期更新、社区讨论正面（star、HN 讨论、引用） |

**一票否决**：需要付费才能看核心内容（可免费预览的除外）；明显 AI 批量生成且未经验证；纯产品广告/榜单；内容与已收录条目高度重复；工具本身（除非它就是学习材料或业界标杆）。

每周新增建议 3–10 条。超过 12 条说明标准放松了，回头再筛一遍。

## 数据格式

### resources.json 条目

```json
{
 "id": "owner-repo 或 域名-路径 的小写短横线形式，唯一",
 "title": "显示标题（仓库用 owner/repo）",
 "url": "https://…（主链接）",
 "extra_links": [{"label": "网站", "url": "https://…"}],
 "category": "classics | patterns | distributed | ddd | adr | ai-arch | tools",
 "type": "official | community | academic | ai",
 "format": "repo | course | docs | article | paper | video | newsletter | book | website",
 "lang": "中文 | 英文 | 中英文 | 多语言…",
 "github": "owner/repo 或 null（有 GitHub 仓库就填，脚本会自动刷新 star）",
 "desc": "一句话中文说明：它讲什么、适合谁、哪里好（≤ 60 字）",
 "note": "可选：注意事项，如"付费订阅"",
 "pick": false,
 "added": "YYYY-MM-DD",
 "score": 8,
 "stars": null, "pushed_at": null, "status": "ok", "last_checked": null
}
```

`pick: true` 只给推荐组合里的核心教材，全站保持 ≤ 6 个。

### reviewed.json

键是规范化 URL（`scripts/common.py` 的 `norm_url`），值：

```json
{"norm-url": {"date": "YYYY-MM-DD", "decision": "accept|reject", "score": 5, "reason": "一句话理由"}}
```

### changelog.json 条目（加在数组最前）

```json
{
 "date": "YYYY-MM-DD",
 "summary": "一句话概括本周更新",
 "stats": {"候选": 50, "审核": 15, "新增": 4},
 "added": ["resource-id", "..."],
 "changed": [{"id": "x", "title": "x", "reason": "URL 迁移到 …"}],
 "removed": [{"id": "x", "title": "x", "reason": "仓库已删除"}],
 "guide_changes": ["学习路线 P5 增加 …"]
}
```

## 不要做

- 不要删除或改写 `UPDATE_PLAYBOOK.md`、`scripts/` 的核心逻辑，除非是修 bug（修了要在汇报里说明）。
- 不要 `git push --force`，不要改仓库设置。
- 不要因为某资料 star 很多就收录；也不要因为 star 少就拒绝（官方文档、文章本来就没有 star）。
- 不要编造链接、star 数或内容描述；所有描述都基于实际打开的页面。
