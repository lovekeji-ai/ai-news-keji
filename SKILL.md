---
name: ai-news-keji
description: 生成 AI/科技新闻日报：从已配置的 Newsletter、RSS、可选外部来源和网站来源抓取、去重、评分并生成 Markdown。用户说“生成日报”、“AI日报”、“今日新闻”、“刷新日报”、“fetch news” 或 “/ai-news-keji” 时使用。
---

# AI 科技新闻日报

从用户配置的信息源生成适合 Obsidian 使用的 AI/科技新闻原始稿和摘要稿。

## 交互语言

所有面向用户的说明、进度更新、错误解释和最终回复都必须使用中文。命令、文件名、配置键、环境变量、URL、产品名和 Newsletter 名称保持原样。

启动工作流时不要用英文开场，例如不要说 “I'll start...”。应使用类似“我先检查 ai-news-keji 的初始化状态。”这样的中文说明。

## 路径

所有文件都相对于 skill 目录解析，也就是包含 `SKILL.md` 的目录。

- 本地配置：`config.yaml`
- 公开配置模板：`config.example.yaml`
- 本地来源：`sources.yaml`
- 公开来源模板：`sources.example.yaml`
- 初始化入口：`scripts/init.py`
- 初始化向导：`scripts/init_wizard.py`
- 摘要模板：`prompts/summary-template.md`
- 健康检查：`scripts/doctor.py`
- RSS 抓取脚本：`scripts/fetch-rss.py`
- IMAP 邮件抓取脚本：`scripts/fetch-email-imap.py`

运行工作流前：

1. 在 skill 目录运行 `python3 scripts/init.py --check`。
2. 如果检查因为缺少 PyYAML 失败，运行 `python3 -m pip install -r requirements.txt`，然后重试一次检查。
3. 如果检查提示首次启动、缺少 `config.yaml`、缺少 `sources.yaml`、`setup.initialized is not true`，或“尚未完成初始化向导”，进入 Agent 分步初始化流程。优先使用 `init.py --check` 输出里的“建议开场”和“第 1 步问题”作为下一条用户消息；如果检查输出里没有这两段，运行 `python3 scripts/init.py` 获取同样的分步提示。
4. 初始化首轮消息固定只包含开场和第 1 步外部集成问题。第 1 步完成前，当前轮不读取 `config.example.yaml` 或 `sources.example.yaml`，也不展示 Newsletter、IMAP、输出目录或个人偏好问题。
5. 分步初始化每轮只处理当前步骤；每一步都先用一句话说明这一步的作用，**然后必须调用 `AskUserQuestion` 工具**让用户用选项卡形式作答，不要让用户在普通对话里手敲文字回答。每个步骤的 `AskUserQuestion` 选项要遵循下面的设计；用户提交答案后再推进下一步：
   - 第 1 步，外部集成：用 `AskUserQuestion` 单条提问，`multiSelect: true`，选项为 `follow-builders`、`BestBlogs`、`ak-rss-digest`、`暂不安装`。每个集成的 label 在已经检测到本机已安装时追加“（本条已安装）”后缀，已安装项默认仍列在选项里供用户保留。说明文案写明这一步用于扩大 AI builder、技术博客和 RSS 覆盖；本轮只收集这个答案。
   - 第 2 步，Newsletter 来源：先读取 `sources.yaml` 或 `sources.example.yaml`，在说明里展示 Newsletter 名称、订阅地址和发件人白名单。再用 `AskUserQuestion` 单选提问，选项为 `imap（现在配置 IMAP 接入）`、`later（先跳过，稍后再配）`、`no（不接入邮件来源）`。
   - 第 2.1 步，IMAP 配置：仅当上一步选 `imap` 时执行。用 **一次** `AskUserQuestion` 调用收集 4 个字段：`IMAP host`、`folder`、`账号环境变量名`、`密码/授权码环境变量名`。每个字段都给出常见预设选项（如 host 给 `imap.gmail.com`、`imap.qq.com`、`imap.163.com`、`outlook.office365.com`；folder 给 `INBOX`；env 名给 `AI_NEWS_IMAP_USERNAME`/`AI_NEWS_IMAP_PASSWORD`），用户可以选项内点选或用“其他”自定义。说明里提醒账号和密码只会通过环境变量提供，不写进 `config.yaml`。
   - 第 3 步，输出目录：用 `AskUserQuestion` 单选提问，选项给出 `~/ai-news-keji/output`（默认）和 1-2 个常见目录（如 `~/Documents/ai-news-keji`），并允许用户用“其他”填写自定义路径。
   - 第 4 步，个人偏好：用 `AskUserQuestion` 单选提问，选项为预置画像（如 `工程 + AI 产品方向`、`研究 + 论文方向`、`创业 + 投资方向`、`暂不填写，使用默认`），并允许用户用“其他”输入完整的多行偏好描述。说明里提醒这一步会影响评分和摘要重点。
6. 收集完全部答案后，把答案写入临时 JSON 文件，然后运行 `python3 scripts/init.py --answers-file <answers.json>`。JSON 字段：`external_skills`、`newsletter.choice`、`newsletter.host`、`newsletter.folder`、`newsletter.username_env`、`newsletter.password_env`、`output_dir`、`preferences`。
7. 写入配置后再次运行 `python3 scripts/init.py --check`。只有检查通过后，才继续读取 `config.yaml`、`sources.yaml` 并抓取新闻。
8. 可选外部 skills 或 CLI 只根据用户在初始化回答里的选择安装。
8.1 用户事后想改某一步配置（例如说“重新配置 Newsletter / 改输出目录 / 改个人偏好 / 重新选外部集成”），运行 `python3 scripts/init.py --reconfigure {external_skills|newsletter|output_dir|preferences}` 获取该步的 `AskUserQuestion` 指令，按同样流程收集答案后运行 `python3 scripts/init.py --answers-file <answers.json> --reconfigure <section>` 写回 `config.yaml`。其他步骤保持原值不动。
9. 解析路径时展开 `~` 和环境变量。
10. 不要把私有输出、原始邮件缓存、token 或用户专属配置写进准备发布的文件。

## 配置

使用 `config.yaml` 控制行为：

- `paths.output_dir`：原始稿和摘要 Markdown 的写入目录
- `paths.filter_rules`：评分规则和兴趣画像；未设置或文件缺失时使用内置示例
- `paths.cache_dir`：原始来源数据和滚动去重状态的缓存目录
- `settings.default_date`：`yesterday` 或 `today`
- `settings.retention_days`：缓存清理窗口
- `settings.dedup_window_days`：跨天去重窗口
- `settings.timezone`：日期过滤时区
- `pipeline.enabled_sources`：要尝试的来源组，例如 `rss`、`email`、`external_skills`、`websites`
- `pipeline.skip_unavailable_sources`：缺少工具或凭据时跳过对应来源，而不是直接失败
- `email.mode`：`none`、`imap` 或 `mcp`
- `email.imap.*`：IMAP host、folder 和凭据环境变量名
- `external_skills.*`：可选命令；只运行 `enabled: true` 的条目
- `notification.method`：`none`、`macos` 或其他用户配置方式

配置不确定时，运行健康检查：

```bash
python3 scripts/doctor.py
```

缺少本地配置时，在 Agent 对话中收集初始化答案，然后写入临时 JSON 并运行：

```bash
python3 scripts/init.py --answers-file <answers.json>
```

抓取来源前，工作流必须通过这个检查：

```bash
python3 scripts/init.py --check
```

## 频率规则

`sources.yaml` 里的每个来源都可以包含 `frequency`：

| frequency | rule |
| --- | --- |
| `daily` | 每次运行都检查。 |
| `weekday` | 目标日期是周六或周日时跳过。 |
| `3x_week` | 每次运行都检查；没有新内容是正常情况。 |
| `weekly` | 如果缓存显示最近 7 天已成功抓取，则跳过。 |
| `irregular` | 每次运行都检查；经常没有新内容是正常情况。 |

被跳过的来源不是失败，也不应该生成空章节。

## 工作流

默认使用 `settings.default_date` 选择的日期。如果用户指定了日期，使用用户指定的日期。

### 1. 抓取来源

工具可用时，并行抓取已启用的来源组。

**RSS**

在 skill 目录运行：

```bash
python3 scripts/fetch-rss.py --date YYYY-MM-DD --config sources.yaml
```

如果缺少 `sources.yaml`，脚本会回退到 `sources.example.yaml`。

**Email Newsletter**

只有当 `pipeline.enabled_sources` 启用了 `email` 时，才使用已配置的 `email` 来源白名单。

支持的模式：

- `none`：跳过邮件来源。
- `imap`：运行内置 IMAP 抓取脚本。凭据必须来自 `email.imap.username_env` 和 `email.imap.password_env` 指定的环境变量。
- `mcp`：当当前 Agent 运行环境提供 email/Gmail MCP 工具时使用该工具。

使用 IMAP 时，在 skill 目录运行：

```bash
python3 scripts/fetch-email-imap.py --date YYYY-MM-DD --config config.yaml --sources sources.yaml
```

IMAP 抓取脚本会搜索目标日期，用 `BODY.PEEK[]` 读取邮件以避免标记为已读，根据配置的发件人和可选 `subject_contains` 过滤邮件，尽可能提取纯文本，并把 JSON 输出到 stdout。

使用 MCP 时，搜索目标日期的邮件，根据配置的发件人和可选 subject 规则过滤，读取匹配邮件，并跳过欢迎邮件、订阅确认、纯赞助邮件、广告和招聘内容。

如果 IMAP 凭据或 MCP 工具不可用，且 `pipeline.skip_unavailable_sources` 为 true，则跳过邮件来源，并记录该来源组不可用。

**外部 skills 和 CLI**

对每个 `enabled: true` 的 `external_skills.*` 条目，运行其配置的命令。命令缺失、目录缺失或非零退出都视为来源失败；如果 `pipeline.skip_unavailable_sources` 为 true，则跳过并记录原因。

用户明确选择外部 skills 后，可通过初始化答案写入配置；如果只是追加安装某个外部 skill，可运行：

```bash
python3 scripts/init.py --skills follow-builders,bestblogs,ak-rss-digest
```

初始化脚本会把原始外部仓库安装到 `external_skills.install_dir` 下，并把选择的 skills 软链到 `external_skills.link_targets`。

它可以安装并启用：

- `follow-builders`：把 `zarazhangrui/follow-builders` clone 到受管理的外部 skill 目录，在其 `scripts/` 目录运行 `npm install`，并软链到已配置的 agent skill 目录。
- `bestblogs`：安装 `@bestblogs/cli`，并可通过 `npx @bestblogs/skills` 安装 BestBlogs agent skills。
- `ak-rss-digest`：clone `rookie-ricardo/erduo-skills`，把其中的 `skills/ak-rss-digest` 子 skill 链接到受管理的外部 skill 目录，并软链到已配置的 agent skill 目录。

**网站来源**

对 Readwise Weekly 等已配置网站来源，仅在浏览器或 web-fetch 能力可用时抓取。使用缓存避免重复抓取同一期周报。

### 2. 缓存原始数据

把原始来源数据写入 `{paths.cache_dir}/YYYY-MM-DD/`。

建议缓存文件：

```text
email-raw.json
rss-raw.json
external-skills.json
websites.json
```

原始邮件缓存可能包含私人内容。请把 `paths.cache_dir` 放在公开 skill 目录之外，且不要提交缓存文件。

清理早于 `settings.retention_days` 的日期缓存目录。

### 3. 维护滚动去重状态

维护 `{paths.cache_dir}/recent-events.json`，保存最近 `settings.dedup_window_days` 天的事件。

对每个抓取项：

1. 提取事件核心：用一句话描述发生了什么。
2. 与最近事件比较。
3. 添加新事件。
4. 只有当延续报道提供实质新信息时才保留。
5. 删除没有新信息的重复转述。

保留延续报道时，标记为 continuation，并在评分时应用 `settings.continuation_penalty`。

### 4. 写入原始稿

写入或追加 `{paths.output_dir}/YYYY-MM-DD.md`。

原始稿要求：

- YAML frontmatter 包含 `created`、`updated`、`type` 和 `sources`
- 每个来源一个章节
- 每个条目包含加粗标题、2-5 句有用摘要和原始链接
- 不包含赞助、广告、招聘或订阅确认内容
- 长 Newsletter 内容应压缩摘要，但保留具体事实、数字、产品名、日期和链接

如果文件已存在，追加新抓取的来源章节，不删除已有内容。

### 5. 生成摘要

如果 `{paths.filter_rules}` 存在则读取它，否则使用 `references/filter-rules.example.md`。

读取完整原始稿，并应用三层处理：

1. 去重并移除噪音。
2. 分别按行业雷达和个人价值两条轨道为每个事件评分。
3. 填充 `prompts/summary-template.md`，写入 `{paths.output_dir}/YYYY-MM-DD 摘要.md`，覆盖该日期的旧摘要。

规则：

- 不要在章节标题后立刻添加解释性文字。
- 完整条目之间用 `---` 分隔。
- 数量是参考而不是硬性配额：2-4 条行业大事、3-5 条对我有用、10-15 条值得关注、2-3 条关键信号。
- 每个事件放在最适合的章节；避免同一事件在主要章节里重复出现。
- 行业重要性不必与用户个人兴趣一致。
- 个人有用可以包括小但可执行的文章。

### 6. 通知

如果 `notification.method` 为 `macos`，只在 macOS 上使用 `osascript`。如果通知不可用或设为 `none`，静默结束，并用中文向用户报告生成的文件路径。

## 失败处理

- 配置允许跳过时，跳过不可用的可选来源。
- 在原始稿末尾记录失败来源。
- 某个 feed 格式错误或某个可选命令失败时，继续处理其他来源。
- 不要根据社交元数据猜测人物角色；有明确 profile 或 bio 字段时才使用。
- 外部评分（例如博客排名分）只作为提示，最终始终应用配置的评分规则。
