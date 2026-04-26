#!/usr/bin/env python3
"""
检查某个目标日期是否已经存在 ai-news-keji 运行产物。

输出 JSON 到 stdout，供 Agent 在抓取前决定是否需要先询问用户。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import yaml
except ImportError:
    print("错误：未安装 PyYAML。请运行：python3 -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


SKILL_ROOT = Path(__file__).resolve().parent.parent
CACHE_FILE_NAMES = (
    "email-raw.json",
    "rss-raw.json",
    "external-skills.json",
    "websites.json",
    "follow-builders.json",
    "bestblogs.json",
    "ak-rss.json",
    "ak-rss-raw.json",
)


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_timezone(name: str):
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone(timedelta(hours=8))


def resolve_target_date(raw_date: str | None, config: dict) -> str:
    settings = config.get("settings") or {}
    tz = load_timezone(str(settings.get("timezone") or "Asia/Shanghai"))
    if raw_date:
        return datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()

    default_date = str(settings.get("default_date") or "yesterday")
    now = datetime.now(tz=tz)
    if default_date == "today":
        return now.date().isoformat()
    return (now - timedelta(days=1)).date().isoformat()


def file_state(path: Path) -> dict:
    exists = path.exists()
    state = {
        "path": str(path),
        "exists": exists,
    }
    if exists and path.is_file():
        stat = path.stat()
        state.update({
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return state


def cache_state(path: Path) -> dict:
    state = {
        "path": str(path),
        "exists": path.exists(),
        "files": [],
        "known_raw_files": [],
    }
    if not path.exists() or not path.is_dir():
        return state

    for item in sorted(path.iterdir()):
        if not item.is_file():
            continue
        stat = item.stat()
        entry = {
            "name": item.name,
            "path": str(item),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        }
        state["files"].append(entry)
        if item.name in CACHE_FILE_NAMES:
            state["known_raw_files"].append(item.name)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Check existing ai-news-keji outputs and cache for a target date")
    parser.add_argument("--date", default=None, help="Target date YYYY-MM-DD (default follows config settings.default_date)")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()
    if not config_path.is_absolute():
        config_path = SKILL_ROOT / config_path
    if not config_path.exists():
        print(f"错误：缺少配置文件：{config_path}", file=sys.stderr)
        return 1

    config = load_yaml(config_path)
    target_date = resolve_target_date(args.date, config)
    paths = config.get("paths") or {}
    output_dir = expand_path(str(paths.get("output_dir") or "~/ai-news-keji/output"))
    cache_dir = expand_path(str(paths.get("cache_dir") or "~/.cache/ai-news-keji"))

    raw_note = file_state(output_dir / f"{target_date}.md")
    summary_note = file_state(output_dir / f"{target_date} 摘要.md")
    daily_cache = cache_state(cache_dir / target_date)

    existing_kinds = []
    if raw_note["exists"]:
        existing_kinds.append("raw_note")
    if summary_note["exists"]:
        existing_kinds.append("summary_note")
    if daily_cache["exists"] and daily_cache["files"]:
        existing_kinds.append("cache")

    print(json.dumps({
        "date": target_date,
        "output_dir": str(output_dir),
        "cache_dir": str(cache_dir),
        "raw_note": raw_note,
        "summary_note": summary_note,
        "daily_cache": daily_cache,
        "existing_kinds": existing_kinds,
        "has_existing": bool(existing_kinds),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
