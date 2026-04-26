# ai-news-keji

AI / 科技新闻日报 Skill。它把 RSS、Newsletter、可选外部命令和网页精选源接到一个 Agent 工作流里，抓取当天信息，去重、评分、分类，然后生成适合放进 Obsidian 或任意 Markdown 知识库的每日新闻原始稿和摘要稿。

这个项目不是另一个信息流阅读器，而是一套“让信息来找你”的个人情报系统骨架：先让高质量源替你筛一遍，再让 Agent 替你做跨源去重、重要性判断和摘要整理。

## 设计思路

`ai-news-keji` 的信息源设计参考了一个多入口信息系统：直接入口包括 RSS、Newsletter、外部 Skill/CLI 和网站精选榜，背后可以连接数百个独立来源。

核心是三层过滤：

```text
重型聚合器
BestBlogs / 机器之心 / Readwise 等，从全网吸入信息
        ↓
编辑精选层
TLDR / The Rundown AI / Ben's Bites / The Neuron 等，由编辑团队二次筛选
        ↓
独家视角层
Latent.Space / DeepLearning.AI / 个人原创 Newsletter 等，提供不可替代的判断
        ↓
你的每日摘要
跨源去重、评分、分类、写入 Markdown
```

默认模板偏 AI 和科技，但刻意保留了工程、创业、创作者经济、Web3、设计和跨领域思考的位置，避免日报变成同质化的 AI 快讯堆叠。

## 能做什么

- 从 `sources.yaml` 中配置的信息源抓取每日内容
- 支持 RSS、邮箱 Newsletter、外部命令/Skill、网页精选源四类入口
- 根据 `frequency` 跳过周末刊、周刊和不定期源
- 缓存原始抓取结果，维护最近事件库，减少跨天重复
- 生成每日原始新闻 Markdown：`YYYY-MM-DD.md`
- 生成每日摘要 Markdown：`YYYY-MM-DD 摘要.md`
- 按“行业雷达”和“个人价值”两条轨道评分
- 对缺失的可选依赖降级处理，不让一个源失败拖垮整份日报

当前仓库里提供了几个确定性脚本：

- `scripts/init.py`：初始化本地配置，并可选安装外部 Skills
- `scripts/init_wizard.py`：首次使用向导，包括 Newsletter 订阅/IMAP、输出目录和个人偏好
- `scripts/fetch-rss.py`：抓取 RSS 并输出 JSON
- `scripts/fetch-email-imap.py`：通过标准 IMAP 抓取 Newsletter 邮件并输出 JSON
- `scripts/doctor.py`：检查依赖、配置、路径和发布安全性

完整的日报生成流程由支持 Skills 的 Agent 根据 [SKILL.md](SKILL.md) 执行。

## 项目结构

```text
ai-news-keji/
├── SKILL.md                         # Agent 工作流说明
├── agents/openai.yaml               # Skill UI 元数据
├── config.example.yaml              # 公共配置模板
├── sources.example.yaml             # 公共信息源模板
├── prompts/summary-template.md      # 摘要输出模板
├── references/filter-rules.example.md
├── scripts/doctor.py
├── scripts/init.py
├── scripts/init_wizard.py
├── scripts/fetch-email-imap.py
├── scripts/fetch-rss.py
├── requirements.txt
└── README.md
```

本地文件 `config.yaml`、`sources.yaml`、缓存、输出和 `.env` 默认不会提交。

## 安装

```bash
git clone <repo-url> ai-news-keji
cd ai-news-keji

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
chmod +x scripts/*.py
```

首次使用由 Agent 在当前对话里完成配置。Agent 触发 `/ai-news-keji` 后会先运行初始化检查；如果发现还没有初始化，就说明接下来会一步步完成配置。每一步都会先解释这一步的作用，再引导用户做选择或填写内容：

- 第 1 步选择是否安装三个集成化 Skill / CLI：`follow-builders`、`BestBlogs`、`ak-rss-digest`
- 第 2 步展示 Newsletter 订阅源清单，并询问是否接入 IMAP、稍后配置或不接入
- 第 3 步确认默认输出目录
- 第 4 步输入个人偏好，用于生成本地 `filter_rules`；跳过时使用内置默认筛选逻辑

Agent 收集完答案后，会把答案写入临时 JSON，并调用：

```bash
.venv/bin/python scripts/init.py --answers-file /path/to/ai-news-keji-init-answers.json
```

初始化完成后，运行强制校验：

```bash
.venv/bin/python scripts/init.py --check
```

当这个 Skill 被 Agent 调用来生成日报时，工作流第一步也会执行同一个校验。如果检测到首次启动、缺少本地配置或向导未完成，Agent 会先提示“检测到 ai-news-keji 还没有完成初始化，我先带你完成初始化向导。”，然后在当前对话里完成上述 5 个步骤。其他校验失败时不会继续抓取新闻，而是提示用户按输出里的 `[next]` 处理。

一次性安装所有可选外部 Skills：

```bash
.venv/bin/python scripts/init.py --install-external-skills
```

## 注册为 Skill

Codex:

```bash
mkdir -p ~/.codex/skills
ln -sfn "$(pwd)" ~/.codex/skills/ai-news-keji
```

Claude 风格的 Skill 目录:

```bash
mkdir -p ~/.claude/skills
ln -sfn "$(pwd)" ~/.claude/skills/ai-news-keji
```

注册后，在支持 Skill 的 Agent 里说类似下面的话即可触发：

```text
使用 ai-news-keji 生成今天的 AI 日报
```

或：

```text
/ai-news-keji 生成 2026-04-25 的日报
```

## 配置

先编辑 `config.yaml`：

```yaml
paths:
  output_dir: ~/ai-news-keji/output
  filter_rules: ~/ai-news-keji/filter-rules.md
  cache_dir: ~/.cache/ai-news-keji

settings:
  default_date: yesterday
  timezone: Asia/Shanghai
  retention_days: 10
  dedup_window_days: 7

pipeline:
  enabled_sources:
    - rss
    - websites
    # - email
  skip_unavailable_sources: true

email:
  mode: none
```

关键项：

- `paths.output_dir`：日报 Markdown 写入目录
- `paths.filter_rules`：你的评分规则和个人兴趣画像；缺失时使用内置示例
- `paths.cache_dir`：缓存目录，建议放在仓库外
- `pipeline.enabled_sources`：启用哪些来源组
- `email.mode`：邮件读取方式，支持 `none`、`imap`、`mcp`
- `external_skills.*.enabled`：是否启用可选外部 Skill 或 CLI
- `notification.method`：`none` 或 `macos`

再编辑 `sources.yaml`。每个源都可以配置频率：

| frequency | 行为 |
| --- | --- |
| `daily` | 每次都查 |
| `weekday` | 目标日期是周末时跳过 |
| `3x_week` | 每次都查，没有新内容也正常 |
| `weekly` | 一周内已成功抓取则跳过 |
| `irregular` | 每次都查，没有新内容也正常 |

## 信息源模板

公开模板包含四类入口。

| 类型 | 示例 | 说明 |
| --- | --- | --- |
| RSS | 量子位、机器之心、三花 AI 快讯 | 中文 AI 和科技媒体，适合作为每日基础盘 |
| Newsletter | TLDR、The Rundown AI、The Neuron、Ben's Bites | 编辑精选层，适合快速判断“今天什么重要” |
| 外部 Skill/CLI | follow-builders、bestblogs、ak-rss-digest | 可选增强源，用于接入更大的博客、X、播客或独立源集合 |
| Website | Readwise Weekly | 众包精选层，用读者高亮行为发现长内容 |

你可以从 `sources.example.yaml` 开始删减。公开模板只是 starter set，不要求全部启用。

## 外部 Skills 初始化

这个 Skill 可以接入三个可选外部来源。它们默认关闭，适合在初始化时按需安装：

| 名称 | 作用 | 安装方式 |
| --- | --- | --- |
| follow-builders | 追踪 AI builders 的 X、播客和官方博客动态 | clone `zarazhangrui/follow-builders`，并在 `scripts/` 里运行 `npm install` |
| BestBlogs | 读取 BestBlogs 精选技术/AI/产品内容 | 安装 `@bestblogs/cli`，并运行 `npx @bestblogs/skills` |
| ak-rss-digest | 聚合独立 RSS 源并做评分摘要 | clone `rookie-ricardo/erduo-skills`，链接其中的 `skills/ak-rss-digest` |

默认目录模型：

```text
~/.local/share/ai-news-keji/
└── external-skills/
    ├── follow-builders/       # 原始 git clone
    ├── erduo-skills/          # 原始 git clone
    └── ak-rss-digest -> erduo-skills/skills/ak-rss-digest

~/.claude/skills/
├── follow-builders -> ~/.local/share/ai-news-keji/external-skills/follow-builders
└── ak-rss-digest -> ~/.local/share/ai-news-keji/external-skills/ak-rss-digest
```

交互式安装：

```bash
.venv/bin/python scripts/init.py
```

只安装指定项：

```bash
.venv/bin/python scripts/init.py --skills follow-builders,bestblogs
```

指定外部 Skill 安装目录：

```bash
.venv/bin/python scripts/init.py --install-dir ~/.local/share/ai-news-keji/external-skills --skills follow-builders,ak-rss-digest
```

指定软链目标目录：

```bash
.venv/bin/python scripts/init.py --link-target ~/.claude/skills --link-target ~/.codex/skills --skills follow-builders,ak-rss-digest
```

BestBlogs 安装后通常还需要登录和冷启动兴趣配置：

```bash
bestblogs auth login
bestblogs intake setup
```

安装完成后，`init.py` 会更新 `config.yaml` 的 `external_skills` 命令，并把 `external_skills` 加入 `pipeline.enabled_sources`。BestBlogs 是 CLI 形态，不放进 `external-skills/`；`follow-builders` 和 `ak-rss-digest` 会放进 `external-skills/` 并软链到 Agent skill 目录。

## IMAP 邮件配置

如果你想抓取 Newsletter，但不想配置 Gmail MCP，可以使用标准 IMAP。

首次运行 `scripts/init.py` 时会先列出 `sources.yaml` 里的 Newsletter 订阅清单，包括名称、分类、频率、发件人和订阅入口。先订阅需要的 Newsletter，再选择 `imap` 接入邮箱。

先在 `config.yaml` 里启用 email：

```yaml
pipeline:
  enabled_sources:
    - rss
    - websites
    - email

email:
  mode: imap
  imap:
    host: imap.gmail.com
    port: 993
    ssl: true
    folder: INBOX
    username_env: AI_NEWS_IMAP_USERNAME
    password_env: AI_NEWS_IMAP_PASSWORD
    max_body_chars: 20000
```

再设置环境变量：

```bash
export AI_NEWS_IMAP_USERNAME="you@example.com"
export AI_NEWS_IMAP_PASSWORD="your-app-password-or-imap-password"
```

对 Gmail，通常需要在 Gmail 设置中启用 IMAP，并使用 App Password 或你的组织允许的等价登录方式。不要把邮箱密码直接写进 `config.yaml`。

IMAP 烟测：

```bash
.venv/bin/python scripts/fetch-email-imap.py --date 2026-04-25 --config config.yaml --sources sources.yaml
```

脚本会：

- 只读取 `sources.yaml` 里 `email` 白名单匹配的发件人
- 支持 `subject_contains` 进一步区分同一个发件人的不同 Newsletter
- 使用 `BODY.PEEK[]` 获取邮件，避免把邮件标记为已读
- 提取 `text/plain` 正文，必要时把 HTML 转成纯文本
- 输出 JSON 到 stdout，不主动写缓存文件

## 检查安装

```bash
.venv/bin/python scripts/doctor.py
```

它会检查：

- 必要文件是否存在
- `PyYAML`、`feedparser` 是否可用
- 本地 `config.yaml` / `sources.yaml` 是否存在
- IMAP 模式下的 host 和环境变量是否配置
- 已启用外部 Skills 的命令和安装路径是否配置
- 输出目录、缓存目录和筛选规则路径是否可访问
- 公开文件里是否残留明显的私人路径

运行日报前更严格的闸门是：

```bash
.venv/bin/python scripts/init.py --check
```

这个命令会在未初始化、配置版本过旧、启用的来源缺少必要配置时失败。

## RSS 烟测

不依赖 Agent，仅验证 RSS 抓取脚本：

```bash
.venv/bin/python scripts/fetch-rss.py --date 2026-04-25 --config sources.example.yaml
```

输出是 JSON：

```json
{
  "date": "2026-04-25",
  "feeds": [],
  "stats": {
    "total_feeds": 0,
    "total_entries": 0,
    "feeds_with_entries": 0,
    "feeds_with_errors": 0
  }
}
```

真实结果取决于 feed 当前可用性。单个 RSS XML 损坏时，脚本会记录该 feed 的错误并继续处理其他源。

## 输出格式

原始文件：

```text
YYYY-MM-DD.md
```

摘要文件：

```text
YYYY-MM-DD 摘要.md
```

摘要遵循 [prompts/summary-template.md](prompts/summary-template.md)，默认包含：

- 今日行业大事
- 今日对我有用
- 值得关注
- 今日关键信号

## 隐私与安全

这个项目可能处理 Newsletter 正文、邮箱内容、个人筛选规则和本地知识库路径。默认 `.gitignore` 会忽略：

- `config.yaml`
- `sources.yaml`
- `.env` / `.env.*`
- `.venv/`
- `cache/`
- 本地构建和运行产物

建议：

- 把 `paths.cache_dir` 放在仓库外
- 不要提交 raw email / newsletter JSON
- 不要把 Telegram token、邮箱凭据或个人知识库路径写进公开模板
- 发布前运行 `scripts/doctor.py`

## 可选依赖

基础 RSS 抓取只需要 Python 依赖。

完整日报可能需要当前 Agent 环境提供：

- IMAP 邮箱账号，或 Gmail/邮箱 MCP：读取 Newsletter
- WebFetch / 浏览器能力：读取网站精选源
- 外部命令或 Skill：如 `bestblogs`、`follow-builders`、`ak-rss-digest`
- macOS：仅当你启用 `notification.method: macos`

缺少这些能力时，Skill 会按配置跳过不可用来源。

## 开发

常用检查：

```bash
.venv/bin/python -m py_compile scripts/init.py scripts/fetch-rss.py scripts/fetch-email-imap.py scripts/doctor.py
.venv/bin/python scripts/doctor.py
```

Skill 规范检查：

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

发布前确认：

```bash
git status --short --ignored
git check-ignore -v config.yaml sources.yaml .venv
```

## License

MIT. See [LICENSE](LICENSE).
