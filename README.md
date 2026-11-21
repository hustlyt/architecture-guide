# 深入学习软件架构设计

学习路线 + 持续更新的资料库：经典书籍、架构模式、分布式系统、DDD、ADR、AI 时代架构。

**网站：** https://hustlyt.github.io/architecture-guide/ · [资料库（可搜索）](https://hustlyt.github.io/architecture-guide/resources.html) · [更新日志](https://hustlyt.github.io/architecture-guide/changelog.html) · [RSS](https://hustlyt.github.io/architecture-guide/feed.xml)

在本仓库根目录运行 `python3 -m http.server 8000 --bind 127.0.0.1 --directory docs`，打开 [本地课程](http://127.0.0.1:8000/) 可阅读当前工作区中的站点。

## 怎么更新

每周一 09:00（北京时间）由定时任务自动运行，流程和质量标准见 [UPDATE_PLAYBOOK.md](UPDATE_PLAYBOOK.md)：

1. `scripts/check.py`：刷新 GitHub Star 和最近提交时间，检查所有链接（连续两次失败才算失效）
2. `scripts/discover.py`：从 GitHub、技术博客 RSS 源、HN、arXiv 搜集候选
3. agent 补充网络搜索，打开原文按 10 分制评分，≥ 7 分才收录
4. `scripts/build.py`：校验数据并生成 `docs/`，推送后由 GitHub Pages 发布

只依赖 Python 3.11+ 标准库和 `gh` CLI。

## 目录

| 路径 | 内容 |
|---|---|
| `data/resources.json` | 资料库（唯一数据源） |
| `data/changelog.json` | 更新日志 |
| `data/reviewed.json` | 已审核过的 URL，避免重复审核 |
| `data/sources.json` | 搜集用的数据源和关键词 |
| `content/` | 教程页面正文：`home.html`、`phases/`（各阶段阅读清单）、`phases.json`、`about.html`，以及样式 |
| `docs/` | 生成的网站（不要手改） |
| `scripts/lookup.py` | 查某个 URL 是否已收录/审核过、相近条目和 GitHub 数据（评估单个链接时用） |

## 学习路线（7 个阶段）

| 阶段 | 主题 | 周次 |
|---|---|---|
| P0 | 架构思维基础 | 第 1 周 |
| P1 | 经典架构模式 | 第 2–3 周 |
| P2 | DDD 与领域建模 | 第 4 周 |
| P3 | 分布式系统原理 | 第 5–6 周 |
| P4 | 架构决策记录 ADR | 第 7 周 |
| P5 | AI 时代的系统架构 | 第 8–9 周 |
| P6 | 架构评审与权衡实战 | 第 10 周 |
