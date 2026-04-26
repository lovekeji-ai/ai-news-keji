---
name: ai-news-keji
description: Generate an AI/technology daily news digest from configured newsletters, RSS feeds, optional external sources, and web sources. Use when the user asks to generate, refresh, or summarize an AI news daily report, including requests like "生成日报", "AI日报", "今日新闻", "刷新日报", "fetch news", or "/ai-news-keji".
---

# AI News Daily

Generate an Obsidian-friendly daily AI/technology news raw note and summary note from user-configured sources.

## Paths

Resolve all files relative to the skill directory, which is the directory containing this `SKILL.md`.

- Local config: `config.yaml`
- Public config template: `config.example.yaml`
- Local sources: `sources.yaml`
- Public sources template: `sources.example.yaml`
- Initializer: `scripts/init.py`
- Initializer wizard: `scripts/init_wizard.py`
- Summary template: `prompts/summary-template.md`
- Health check: `scripts/doctor.py`
- RSS fetcher: `scripts/fetch-rss.py`
- IMAP email fetcher: `scripts/fetch-email-imap.py`

Before running the workflow:

1. Run `python3 scripts/init.py --check` from the skill directory.
2. If the check fails because PyYAML is missing, run `python3 -m pip install -r requirements.txt`, then retry the check once.
3. If the check reports first-time setup, missing `config.yaml`, missing `sources.yaml`, or `setup.initialized is not true`, tell the user: `检测到 ai-news-keji 还没有完成初始化，开始进行初始化。` Then run `python3 scripts/init.py` so the user can choose recommended integrations, newsletter setup, output directory, and filtering preferences. If interactive input is unavailable, stop and tell the user to run `python3 scripts/init.py` in a terminal; use `python3 scripts/init.py --yes` only when the user explicitly wants a quick default setup.
4. If the check warns that guided setup has not been completed, continue only if the technical check passes, but tell the user they can improve source coverage and personalization by running `python3 scripts/init.py`.
5. If the check still fails after the first-time initialization path, stop the workflow. Report the failed check output and the `[next]` command recommended by `init.py --check`.
6. Do not install optional external skills or CLIs unless the user explicitly confirms the setup prompt or asks for them.
7. Read `config.yaml` and `sources.yaml` only after the init check passes.
8. Expand `~` and environment variables in paths.
9. Never write private output, raw email caches, tokens, or user-specific config into files intended for publishing.

## Configuration

Use `config.yaml` for behavior:

- `paths.output_dir`: directory for raw and summary Markdown files
- `paths.filter_rules`: scoring and interest-profile rules; use the bundled example if unset or missing
- `paths.cache_dir`: cache directory for raw source data and rolling dedup state
- `settings.default_date`: `yesterday` or `today`
- `settings.retention_days`: cache cleanup window
- `settings.dedup_window_days`: rolling event dedup window
- `settings.timezone`: timezone for date filtering
- `pipeline.enabled_sources`: source groups to attempt, such as `rss`, `email`, `external_skills`, and `websites`
- `pipeline.skip_unavailable_sources`: skip missing tools or credentials instead of failing
- `email.mode`: `none`, `imap`, or `mcp`
- `email.imap.*`: IMAP host, folder, and environment variable names for credentials
- `external_skills.*`: optional commands; only run entries with `enabled: true`
- `notification.method`: `none`, `macos`, or another user-configured method

Run the health check when setup is uncertain:

```bash
python3 scripts/doctor.py
```

Run first-time initialization when local config is missing or the user wants optional external skills:

```bash
python3 scripts/init.py
```

The workflow must pass this check before fetching sources:

```bash
python3 scripts/init.py --check
```

## Frequency Rules

Each source in `sources.yaml` can include `frequency`:

| frequency | rule |
| --- | --- |
| `daily` | Check every run. |
| `weekday` | Skip when the target date is Saturday or Sunday. |
| `3x_week` | Check every run; no new content is normal. |
| `weekly` | Skip when the cache shows a successful fetch in the last 7 days. |
| `irregular` | Check every run; no new content is normal. |

Skipped sources are not failures and should not produce empty sections.

## Workflow

Default to the date selected by `settings.default_date`. If the user gives a date, use that date.

### 1. Fetch Sources

Fetch enabled source groups in parallel when tools are available.

**RSS**

Run from the skill directory:

```bash
python3 scripts/fetch-rss.py --date YYYY-MM-DD --config sources.yaml
```

If `sources.yaml` is missing, the script falls back to `sources.example.yaml`.

**Email newsletters**

Use the configured `email` source allowlist only when `email` is enabled in `pipeline.enabled_sources`.

Supported modes:

- `none`: skip email sources.
- `imap`: run the bundled IMAP fetcher. Credentials must come from environment variables named by `email.imap.username_env` and `email.imap.password_env`.
- `mcp`: use an email/Gmail MCP tool when the current Agent runtime provides one.

For IMAP, run from the skill directory:

```bash
python3 scripts/fetch-email-imap.py --date YYYY-MM-DD --config config.yaml --sources sources.yaml
```

The IMAP fetcher searches the target date, reads messages with `BODY.PEEK[]` so messages are not marked read, filters by the configured sender and optional `subject_contains`, extracts plain text where possible, and prints JSON to stdout.

For MCP, search messages for the target date, filter by the configured sender and optional subject rule, read matching messages, and skip welcome emails, subscription confirmations, sponsor-only emails, ads, and hiring posts.

If IMAP credentials or MCP tools are unavailable and `pipeline.skip_unavailable_sources` is true, skip email sources and record the source group as unavailable.

**External skills and CLIs**

For each `external_skills.*` entry with `enabled: true`, run the configured command. Treat missing commands, missing directories, and non-zero exits as source failures unless `pipeline.skip_unavailable_sources` is true, in which case skip and record the reason.

To configure optional external skills, run:

```bash
python3 scripts/init.py
```

The initializer installs original external repositories under `external_skills.install_dir` and symlinks selected skills into `external_skills.link_targets`.

It can install and enable:

- `follow-builders`: clones `zarazhangrui/follow-builders` into the managed external skill directory, runs `npm install` in its `scripts/` folder, and symlinks the skill into configured agent skill directories.
- `bestblogs`: installs `@bestblogs/cli` and optionally BestBlogs agent skills with `npx @bestblogs/skills`.
- `ak-rss-digest`: clones `rookie-ricardo/erduo-skills`, links its `skills/ak-rss-digest` subskill under the managed external skill directory, and symlinks it into configured agent skill directories.

**Web sources**

For configured website sources such as Readwise Weekly, fetch only when browser/web-fetch capability is available. Use the cache to avoid repeatedly fetching the same weekly issue.

### 2. Cache Raw Data

Write raw source data under `{paths.cache_dir}/YYYY-MM-DD/`.

Suggested cache files:

```text
email-raw.json
rss-raw.json
external-skills.json
websites.json
```

Raw email caches may contain private content. Keep `paths.cache_dir` outside the published skill folder and never commit cache files.

Clean date cache directories older than `settings.retention_days`.

### 3. Maintain Rolling Dedup State

Maintain `{paths.cache_dir}/recent-events.json` with events from the last `settings.dedup_window_days`.

For each fetched item:

1. Extract the event core: one sentence describing what happened.
2. Compare it with recent events.
3. Add new events.
4. Keep continuation reports only when they add substantial new information.
5. Drop repeated retellings with no new information.

When a continuation report is kept, mark it as continuation and apply `settings.continuation_penalty` during scoring.

### 4. Write Raw Note

Write or append `{paths.output_dir}/YYYY-MM-DD.md`.

Raw note requirements:

- YAML frontmatter with `created`, `updated`, `type`, and `sources`
- one section per source
- each item includes a bold title, 2-5 useful sentences, and the original link
- no sponsor, ad, hiring, or subscription-confirmation content
- long newsletter content should be condensed while preserving concrete facts, numbers, product names, dates, and links

If the file already exists, append newly fetched source sections without deleting previous content.

### 5. Generate Summary

Read `{paths.filter_rules}` when it exists; otherwise use `references/filter-rules.example.md`.

Read the full raw note and apply three layers:

1. Deduplicate and remove noise.
2. Score each event on both the industry-radar track and the personal-value track.
3. Fill `prompts/summary-template.md` and write `{paths.output_dir}/YYYY-MM-DD 摘要.md`, overwriting the previous summary for that date.

Rules:

- Do not add explanatory text immediately after section headings.
- Separate full items with `---`.
- Expected counts are guides, not quotas: 2-4 industry items, 3-5 personally useful items, 10-15 watch-list items, and 2-3 key signals.
- Put each event in its best section; avoid duplicating the same event across major sections.
- Industry importance does not need to match the user's personal interests.
- Personal usefulness can include small but actionable articles.

### 6. Notify

If `notification.method` is `macos`, use `osascript` only on macOS. If notifications are unavailable or set to `none`, finish silently and report the generated file paths to the user.

## Failure Handling

- Skip unavailable optional sources when configured to do so.
- Record failed sources at the end of the raw note.
- Continue when one feed is malformed or one optional command fails.
- Do not guess a person's role from social metadata; use explicit profile or bio fields when present.
- Treat external scores, such as blog ranking scores, as hints; always apply the configured scoring rules.
