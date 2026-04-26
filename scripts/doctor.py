#!/usr/bin/env python3
"""
Check whether ai-news-keji is ready to run in the current environment.
"""
from __future__ import annotations

import importlib.util
import os
import platform
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


SKILL_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_PATTERNS = tuple(
    pattern
    for pattern in (
        str(Path.home()),
        Path.home().name,
        "Second" + " Brain",
    )
    if pattern
)
PUBLIC_FILES = (
    "SKILL.md",
    "README.md",
    "config.example.yaml",
    "sources.example.yaml",
    "requirements.txt",
    "scripts/init.py",
    "scripts/init_wizard.py",
    "scripts/fetch-email-imap.py",
    "scripts/fetch-rss.py",
    "scripts/doctor.py",
    "prompts/summary-template.md",
    "references/filter-rules.example.md",
    "agents/openai.yaml",
)


def status(kind: str, message: str) -> None:
    print(f"[{kind}] {message}")


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def load_yaml(path: Path) -> dict:
    if yaml is None:
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_required_files() -> int:
    problems = 0
    for relative in PUBLIC_FILES:
        path = SKILL_ROOT / relative
        if path.exists():
            status("ok", f"found {relative}")
        else:
            status("error", f"missing {relative}")
            problems += 1
    return problems


def check_python_dependencies() -> int:
    problems = 0
    for module, package in (("yaml", "PyYAML"), ("feedparser", "feedparser")):
        if has_module(module):
            status("ok", f"python module available: {module}")
        else:
            status("error", f"missing Python package: {package}. Run: python3 -m pip install -r requirements.txt")
            problems += 1
    return problems


def check_local_config() -> int:
    problems = 0
    config_path = SKILL_ROOT / "config.yaml"
    sources_path = SKILL_ROOT / "sources.yaml"

    if config_path.exists():
        status("ok", "local config.yaml exists")
        if yaml is not None:
            config = load_yaml(config_path)
            check_setup_config(config)
            paths = config.get("paths", {})
            for key in ("output_dir", "cache_dir"):
                raw = paths.get(key)
                if not raw:
                    status("warn", f"paths.{key} is not set")
                    continue
                expanded = Path(os.path.expandvars(os.path.expanduser(str(raw))))
                if expanded.exists():
                    status("ok", f"paths.{key} exists: {expanded}")
                else:
                    status("warn", f"paths.{key} does not exist yet: {expanded}")
            filter_rules = paths.get("filter_rules")
            if filter_rules:
                expanded = Path(os.path.expandvars(os.path.expanduser(str(filter_rules))))
                if expanded.exists():
                    status("ok", f"paths.filter_rules exists: {expanded}")
                else:
                    status("warn", "paths.filter_rules missing; bundled example rules will be used")
            check_email_config(config)
            check_external_skills(config)
    else:
        status("warn", "config.yaml missing. Copy config.example.yaml to config.yaml and edit local paths.")

    if sources_path.exists():
        status("ok", "local sources.yaml exists")
    else:
        status("warn", "sources.yaml missing. RSS fetcher will fall back to sources.example.yaml.")

    if platform.system() != "Darwin":
        status("info", "macOS notifications are unavailable on this platform; use notification.method: none")

    return problems


def check_email_config(config: dict) -> None:
    pipeline = config.get("pipeline", {})
    enabled_sources = pipeline.get("enabled_sources") or []
    email_config = config.get("email") or {}
    mode = email_config.get("mode", "none")

    if mode == "none" and "email" not in enabled_sources:
        status("info", "email source disabled")
        return

    if mode == "imap":
        imap_config = email_config.get("imap") or {}
        host = imap_config.get("host")
        username_env = imap_config.get("username_env") or "AI_NEWS_IMAP_USERNAME"
        password_env = imap_config.get("password_env") or "AI_NEWS_IMAP_PASSWORD"

        if host:
            status("ok", f"email.imap.host configured: {host}")
        else:
            status("warn", "email.mode is imap but email.imap.host is missing")

        if os.environ.get(username_env):
            status("ok", f"IMAP username env set: {username_env}")
        else:
            status("warn", f"IMAP username env not set: {username_env}")

        if os.environ.get(password_env):
            status("ok", f"IMAP password env set: {password_env}")
        else:
            status("warn", f"IMAP password env not set: {password_env}")
        return

    if mode == "mcp":
        status("info", "email.mode is mcp; ensure the current Agent runtime provides an email/Gmail MCP tool")
        return

    if "email" in enabled_sources:
        status("warn", f"email source is enabled but email.mode is {mode!r}; expected none, imap, or mcp")


def check_setup_config(config: dict) -> None:
    setup = config.get("setup") or {}
    if setup.get("initialized") is True:
        status("ok", "setup.initialized is true")
    else:
        status("warn", "setup.initialized is not true; run: python3 scripts/init.py")

    version = setup.get("init_schema_version")
    if version:
        status("ok", f"setup.init_schema_version: {version}")
    else:
        status("warn", "setup.init_schema_version is missing")


def check_external_skills(config: dict) -> None:
    external_config = config.get("external_skills") or {}
    if not external_config:
        status("info", "external skills not configured")
        return

    install_dir = external_config.get("install_dir")
    if install_dir:
        expanded = Path(os.path.expandvars(os.path.expanduser(str(install_dir))))
        if expanded.exists():
            status("ok", f"external_skills.install_dir exists: {expanded}")
        else:
            status("warn", f"external_skills.install_dir missing: {expanded}")

    link_targets = external_config.get("link_targets") or []
    for target in link_targets:
        expanded = Path(os.path.expandvars(os.path.expanduser(str(target))))
        if expanded.exists():
            status("ok", f"external skill link target exists: {expanded}")
        else:
            status("warn", f"external skill link target missing: {expanded}")

    enabled = []
    for name, item in external_config.items():
        if not isinstance(item, dict):
            continue
        if item.get("enabled"):
            enabled.append(name)
            command = item.get("command")
            if command:
                status("ok", f"external skill enabled: {name}")
            else:
                status("warn", f"external skill {name} is enabled but command is missing")

            install_path = item.get("install_path")
            if install_path:
                expanded = Path(os.path.expandvars(os.path.expanduser(str(install_path))))
                if expanded.exists():
                    status("ok", f"{name} install_path exists: {expanded}")
                else:
                    status("warn", f"{name} install_path missing: {expanded}")

    if not enabled:
        status("info", "external skills disabled")


def check_publish_safety() -> int:
    problems = 0
    for relative in PUBLIC_FILES:
        path = SKILL_ROOT / relative
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in PRIVATE_PATTERNS:
            if pattern in text:
                status("error", f"private-looking pattern {pattern!r} found in {relative}")
                problems += 1
    return problems


def main() -> int:
    print(f"ai-news-keji doctor: {SKILL_ROOT}")
    problems = 0

    problems += check_required_files()
    problems += check_python_dependencies()
    problems += check_local_config()
    problems += check_publish_safety()

    if problems:
        status("error", f"{problems} issue(s) need attention")
        return 1

    status("ok", "doctor checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
