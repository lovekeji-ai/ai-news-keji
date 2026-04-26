#!/usr/bin/env python3
"""
Initialize ai-news-keji for local use.

This script creates local config files, records setup state, and can install
optional external skills into a managed directory while symlinking them into
Claude/Codex skill directories.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. Run: python3 -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


SKILL_ROOT = Path(__file__).resolve().parent.parent
SETUP_SCHEMA_VERSION = 1
DEFAULT_INSTALL_DIR = "~/.local/share/ai-news-keji/external-skills"
DEFAULT_LINK_TARGETS = ["~/.claude/skills"]

EXTERNAL_SKILLS = {
    "follow-builders": {
        "label": "follow-builders",
        "description": "AI builder digest from X, podcasts, and official AI blogs.",
        "repo": "https://github.com/zarazhangrui/follow-builders.git",
        "install_kind": "git-node-skill",
        "clone_dir": "follow-builders",
        "link_name": "follow-builders",
    },
    "bestblogs": {
        "label": "BestBlogs",
        "description": "BestBlogs CLI and optional agent skills for curated technical reading.",
        "repo": "https://github.com/ginobefun/bestblogs",
        "install_kind": "npm-cli",
        "command": "bestblogs discover today --limit 20 --json 2>/dev/null",
        "next_steps": [
            "Run: bestblogs auth login",
            "Optional: bestblogs intake setup",
        ],
    },
    "ak-rss-digest": {
        "label": "AK RSS Digest",
        "description": "RSS/Atom digest from rookie-ricardo/erduo-skills.",
        "repo": "https://github.com/rookie-ricardo/erduo-skills.git",
        "install_kind": "git-subskill",
        "repo_dir": "erduo-skills",
        "link_name": "ak-rss-digest",
    },
}


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def shell_path(path) -> str:
    return shlex.quote(str(path))


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def copy_if_missing(source: Path, target: Path, force: bool = False, dry_run: bool = False) -> bool:
    if target.exists() and not force:
        print(f"[ok] {target.name} already exists")
        return False
    print(f"[ok] create {target.name} from {source.name}")
    if dry_run:
        return True
    shutil.copyfile(source, target)
    return True


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_command(cmd: list[str], cwd: Optional[Path] = None, dry_run: bool = False) -> None:
    cwd_text = f" (cwd: {cwd})" if cwd else ""
    print(f"[run] {' '.join(shlex.quote(part) for part in cmd)}{cwd_text}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def prompt_yes_no(question: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    answer = input(f"{question} [{suffix}] ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes", "是", "好"}


def ensure_directory(path: Path, dry_run: bool = False) -> None:
    print(f"[ok] ensure directory: {path}")
    if not dry_run:
        path.mkdir(parents=True, exist_ok=True)


def ensure_parent(path: Path, dry_run: bool = False) -> None:
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)


def path_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".ai-news-keji-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def clone_or_update(repo: str, path: Path, dry_run: bool = False) -> None:
    if path.exists():
        if (path / ".git").exists():
            run_command(["git", "-C", str(path), "pull", "--ff-only"], dry_run=dry_run)
        else:
            print(f"[warn] {path} exists and is not a git repository; skipping clone")
        return
    run_command(["git", "clone", repo, str(path)], dry_run=dry_run)


def symlink_force(source: Path, target: Path, dry_run: bool = False) -> None:
    print(f"[ok] link {target} -> {source}")
    if dry_run:
        return
    ensure_parent(target)
    if target.is_symlink() or target.exists():
        if target.is_dir() and not target.is_symlink():
            print(f"[warn] {target} exists as a directory; leaving it unchanged")
            return
        target.unlink()
    target.symlink_to(source, target_is_directory=True)


def install_follow_builders(install_dir: Path, link_targets: list[Path], dry_run: bool = False) -> dict:
    meta = EXTERNAL_SKILLS["follow-builders"]
    install_path = install_dir / meta["clone_dir"]
    clone_or_update(meta["repo"], install_path, dry_run=dry_run)

    scripts_dir = install_path / "scripts"
    if command_exists("npm"):
        run_command(["npm", "install"], cwd=scripts_dir, dry_run=dry_run)
    else:
        print("[warn] npm is not installed; follow-builders dependencies were not installed")

    link_name = meta["link_name"]
    link_skill_to_targets(install_path, link_name, link_targets, dry_run=dry_run)

    return {
        "enabled": True,
        "install_kind": meta["install_kind"],
        "repo": meta["repo"],
        "install_path": str(install_path),
        "link_name": link_name,
        "command": f"cd {shell_path(scripts_dir)} && node prepare-digest.js 2>/dev/null",
    }


def install_bestblogs(dry_run: bool = False) -> dict:
    meta = EXTERNAL_SKILLS["bestblogs"]

    if command_exists("npm"):
        run_command(["npm", "install", "-g", "@bestblogs/cli"], dry_run=dry_run)
    else:
        print("[warn] npm is not installed; @bestblogs/cli was not installed")

    if command_exists("npx"):
        run_command(["npx", "@bestblogs/skills"], dry_run=dry_run)
    else:
        print("[warn] npx is not installed; BestBlogs agent skills were not installed")

    for step in meta.get("next_steps", []):
        print(f"[next] {step}")

    return {
        "enabled": True,
        "install_kind": meta["install_kind"],
        "repo": meta["repo"],
        "command": meta["command"],
    }


def install_ak_rss_digest(install_dir: Path, link_targets: list[Path], dry_run: bool = False) -> dict:
    meta = EXTERNAL_SKILLS["ak-rss-digest"]
    repo_path = install_dir / meta["repo_dir"]
    source_path = repo_path / "skills" / "ak-rss-digest"
    install_path = install_dir / "ak-rss-digest"
    link_name = meta["link_name"]

    clone_or_update(meta["repo"], repo_path, dry_run=dry_run)
    symlink_force(source_path, install_path, dry_run=dry_run)
    link_skill_to_targets(install_path, link_name, link_targets, dry_run=dry_run)

    return {
        "enabled": True,
        "install_kind": meta["install_kind"],
        "repo": meta["repo"],
        "install_path": str(install_path),
        "source_path": str(source_path),
        "repo_path": str(repo_path),
        "link_name": link_name,
        "command": f"cd {shell_path(repo_path)} && python3 skills/ak-rss-digest/scripts/fetch_today_feed_items.py --days 1 --timezone Asia/Shanghai --format json 2>/dev/null",
    }


def link_skill_to_targets(source: Path, link_name: str, link_targets: list[Path], dry_run: bool = False) -> None:
    for target_dir in link_targets:
        ensure_directory(target_dir, dry_run=dry_run)
        symlink_force(source, target_dir / link_name, dry_run=dry_run)


def install_external_skill(name: str, install_dir: Path, link_targets: list[Path], dry_run: bool = False) -> dict:
    if name == "follow-builders":
        return install_follow_builders(install_dir, link_targets, dry_run=dry_run)
    if name == "bestblogs":
        return install_bestblogs(dry_run=dry_run)
    if name == "ak-rss-digest":
        return install_ak_rss_digest(install_dir, link_targets, dry_run=dry_run)
    raise ValueError(f"Unknown external skill: {name}")


def parse_skill_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    names = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [name for name in names if name not in EXTERNAL_SKILLS]
    if unknown:
        raise SystemExit(f"Unknown external skill(s): {', '.join(unknown)}")
    return names


def choose_external_skills(args) -> list[str]:
    explicit = parse_skill_list(args.skills)
    if explicit:
        return explicit
    if args.install_external_skills:
        return list(EXTERNAL_SKILLS)
    if args.yes:
        return []

    selected = []
    print("\nOptional external skills:")
    for name, meta in EXTERNAL_SKILLS.items():
        if prompt_yes_no(f"Install and enable {meta['label']}? {meta['description']}", default=False):
            selected.append(name)
    return selected


def choose_link_targets(args, selected: list[str]) -> list[Path]:
    raw_targets: list[str] = []

    if args.skill_dir:
        print("[warn] --skill-dir is deprecated; use --link-target instead")
        raw_targets.append(args.skill_dir)

    if args.link_target:
        raw_targets.extend(args.link_target)

    if args.no_link:
        raw_targets = []

    if not raw_targets and selected:
        if args.yes or args.install_external_skills or args.skills:
            raw_targets = DEFAULT_LINK_TARGETS[:]
        else:
            if prompt_yes_no("Register external skills in ~/.claude/skills via symlinks?", default=True):
                raw_targets.append("~/.claude/skills")
            if prompt_yes_no("Also register external skills in ~/.codex/skills via symlinks?", default=False):
                raw_targets.append("~/.codex/skills")

    return [expand_path(target) for target in raw_targets]


def create_local_configs(force: bool = False, dry_run: bool = False) -> None:
    copy_if_missing(SKILL_ROOT / "config.example.yaml", SKILL_ROOT / "config.yaml", force=force, dry_run=dry_run)
    copy_if_missing(SKILL_ROOT / "sources.example.yaml", SKILL_ROOT / "sources.yaml", force=force, dry_run=dry_run)


def update_pipeline(config: dict, selected: list[str]) -> None:
    pipeline = config.setdefault("pipeline", {})
    enabled_sources = pipeline.setdefault("enabled_sources", ["rss", "websites"])
    if selected and "external_skills" not in enabled_sources:
        enabled_sources.append("external_skills")


def update_setup_state(config: dict, selected: list[str]) -> None:
    setup = config.setdefault("setup", {})
    setup["initialized"] = True
    setup["init_schema_version"] = SETUP_SCHEMA_VERSION
    setup["initialized_at"] = datetime.now(timezone.utc).isoformat()
    setup["selected_external_skills"] = selected


def configure_external_skills(config: dict, selected: list[str], install_dir: Path, link_targets: list[Path], dry_run: bool = False) -> None:
    external_config = config.setdefault("external_skills", {})
    external_config["install_dir"] = str(install_dir)
    external_config["link_targets"] = [str(path) for path in link_targets]

    for name in selected:
        print(f"\nInstalling {name}...")
        external_config[name] = install_external_skill(name, install_dir, link_targets, dry_run=dry_run)


def create_runtime_dirs(config: dict, dry_run: bool = False) -> None:
    paths = config.get("paths", {})
    for key in ("output_dir", "cache_dir"):
        raw = paths.get(key)
        if raw:
            ensure_directory(expand_path(str(raw)), dry_run=dry_run)


def check_config() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    first_time_setup = False
    config_path = SKILL_ROOT / "config.yaml"
    sources_path = SKILL_ROOT / "sources.yaml"

    if not config_path.exists():
        first_time_setup = True
        errors.append("config.yaml is missing. Run: python3 scripts/init.py")
        add_init_recommendations(recommendations, first_time=True)
        return print_check_result(errors, warnings, recommendations, first_time_setup=first_time_setup)
    if not sources_path.exists():
        first_time_setup = True
        errors.append("sources.yaml is missing. Run: python3 scripts/init.py")
        add_init_recommendations(recommendations, first_time=True)

    config = load_yaml(config_path)
    setup = config.get("setup") or {}
    if setup.get("initialized") is not True:
        first_time_setup = True
        errors.append("setup.initialized is not true. Run: python3 scripts/init.py")
        add_init_recommendations(recommendations, first_time=True)
    if int(setup.get("init_schema_version") or 0) < SETUP_SCHEMA_VERSION:
        errors.append(f"setup.init_schema_version is outdated. Run: python3 scripts/init.py --force or migrate config.yaml")
        add_init_recommendations(recommendations)

    paths = config.get("paths") or {}
    for key in ("output_dir", "cache_dir"):
        raw = paths.get(key)
        if not raw:
            errors.append(f"paths.{key} is missing")
            add_init_recommendations(recommendations)
            continue
        path = expand_path(str(raw))
        if not path.exists():
            errors.append(f"paths.{key} does not exist: {path}")
            add_init_recommendations(recommendations)
        elif not path_writable(path):
            errors.append(f"paths.{key} is not writable: {path}")

    pipeline = config.get("pipeline") or {}
    enabled_sources = pipeline.get("enabled_sources") or []
    if not enabled_sources:
        errors.append("pipeline.enabled_sources is empty")

    check_email(errors, warnings, config, enabled_sources)
    check_external(errors, warnings, recommendations, config, enabled_sources)

    return print_check_result(errors, warnings, recommendations, first_time_setup=first_time_setup)


def check_email(errors: list[str], warnings: list[str], config: dict, enabled_sources: list[str]) -> None:
    if "email" not in enabled_sources:
        return

    pipeline = config.get("pipeline") or {}
    skip_unavailable = bool(pipeline.get("skip_unavailable_sources"))
    email_config = config.get("email") or {}
    mode = email_config.get("mode", "none")

    def report_email_problem(message: str) -> None:
        if skip_unavailable:
            warnings.append(f"{message}; source will be skipped because pipeline.skip_unavailable_sources is true")
        else:
            errors.append(message)

    if mode == "none":
        report_email_problem("email source is enabled but email.mode is none")
        return
    if mode == "mcp":
        warnings.append("email.mode is mcp; make sure the current Agent runtime provides an email/Gmail MCP tool")
        return
    if mode != "imap":
        report_email_problem(f"unsupported email.mode: {mode}")
        return

    imap_config = email_config.get("imap") or {}
    if not imap_config.get("host"):
        report_email_problem("email.imap.host is missing")

    username_env = imap_config.get("username_env") or "AI_NEWS_IMAP_USERNAME"
    password_env = imap_config.get("password_env") or "AI_NEWS_IMAP_PASSWORD"
    if not os.environ.get(username_env):
        report_email_problem(f"IMAP username env is missing: {username_env}")
    if not os.environ.get(password_env):
        report_email_problem(f"IMAP password env is missing: {password_env}")


def check_external(errors: list[str], warnings: list[str], recommendations: list[str], config: dict, enabled_sources: list[str]) -> None:
    if "external_skills" not in enabled_sources:
        return

    pipeline = config.get("pipeline") or {}
    skip_unavailable = bool(pipeline.get("skip_unavailable_sources"))
    external_config = config.get("external_skills") or {}
    enabled_items = {
        name: item
        for name, item in external_config.items()
        if isinstance(item, dict) and item.get("enabled")
    }
    if not enabled_items:
        message = "external_skills source is enabled but no external skill entry is enabled"
        if skip_unavailable:
            warnings.append(f"{message}; source group will be skipped because pipeline.skip_unavailable_sources is true")
        else:
            errors.append(message)
        recommendations.append("Disable external_skills in config.yaml or run: python3 scripts/init.py --skills follow-builders,bestblogs,ak-rss-digest")
        return

    def report_external_problem(message: str, recommendation: str) -> None:
        if skip_unavailable:
            warnings.append(f"{message}; source will be skipped because pipeline.skip_unavailable_sources is true")
        else:
            errors.append(message)
        recommendations.append(recommendation)

    install_dir = external_config.get("install_dir")
    if install_dir and not expand_path(str(install_dir)).exists():
        warnings.append(f"external_skills.install_dir does not exist yet: {expand_path(str(install_dir))}")

    for name, item in enabled_items.items():
        command = item.get("command")
        if not command:
            report_external_problem(
                f"external skill {name} is enabled but command is missing",
                f"Reconfigure {name}: python3 scripts/init.py --skills {name}",
            )

        if name == "bestblogs":
            if not command_exists("bestblogs"):
                report_external_problem(
                    "bestblogs is enabled but the bestblogs command is not available",
                    "Install BestBlogs CLI: python3 scripts/init.py --skills bestblogs",
                )
            continue

        install_path = item.get("install_path")
        if not install_path:
            report_external_problem(
                f"external skill {name} is enabled but install_path is missing",
                f"Install {name}: python3 scripts/init.py --skills {name}",
            )
            continue
        if not expand_path(str(install_path)).exists():
            report_external_problem(
                f"external skill {name} install_path is missing: {expand_path(str(install_path))}",
                f"Install {name}: python3 scripts/init.py --skills {name}",
            )


def add_init_recommendations(recommendations: list[str], first_time: bool = False) -> None:
    if first_time:
        recommendations.append("First-time setup: python3 scripts/init.py --yes")
        recommendations.append("Interactive setup with optional sources: python3 scripts/init.py")
        return
    recommendations.append("Interactive setup: python3 scripts/init.py")
    recommendations.append("Minimal non-interactive setup: python3 scripts/init.py --yes")


def unique_items(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def print_check_result(
    errors: list[str],
    warnings: list[str],
    recommendations: list[str],
    first_time_setup: bool = False,
) -> int:
    if first_time_setup and errors:
        print("[info] first-time setup detected: local initialization has not completed")
        print("[info] safe default initialization: python3 scripts/init.py --yes")
    for warning in warnings:
        print(f"[warn] {warning}")
    for error in errors:
        print(f"[error] {error}")
    if errors:
        print("[error] init check failed")
        for recommendation in unique_items(recommendations) or ["Run: python3 scripts/init.py"]:
            print(f"[next] {recommendation}")
        return 1
    for recommendation in unique_items(recommendations):
        print(f"[next] Optional: {recommendation}")
    print("[ok] init check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize ai-news-keji local config and optional external skills")
    parser.add_argument("--check", action="store_true", help="Validate that init has completed and enabled sources are usable")
    parser.add_argument("--yes", action="store_true", help="Use non-interactive defaults; does not install optional external skills")
    parser.add_argument("--force", action="store_true", help="Overwrite config.yaml and sources.yaml from examples")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing files or installing packages")
    parser.add_argument("--install-dir", default=DEFAULT_INSTALL_DIR, help="Managed directory for external skill source checkouts")
    parser.add_argument("--link-target", action="append", default=None, help="Skill directory to receive symlinks; can be repeated")
    parser.add_argument("--no-link", action="store_true", help="Install external skill sources without symlinking them into agent skill dirs")
    parser.add_argument("--skill-dir", default=None, help="Deprecated alias for --link-target")
    parser.add_argument("--install-external-skills", action="store_true", help="Install and enable all optional external skills")
    parser.add_argument("--skills", default=None, help="Comma-separated external skills to install: follow-builders,bestblogs,ak-rss-digest")
    args = parser.parse_args()

    if args.check:
        return check_config()

    config_path = SKILL_ROOT / "config.yaml"
    sources_path = SKILL_ROOT / "sources.yaml"
    existing_config = config_path.exists()
    existing_sources = sources_path.exists()

    print(f"ai-news-keji init: {SKILL_ROOT}")
    if not existing_config or not existing_sources:
        print("[info] first-time setup detected; creating local config files and runtime directories")

    if not command_exists("git"):
        print("[warn] git is not installed; git-based external skills cannot be installed")

    create_local_configs(force=args.force, dry_run=args.dry_run)
    config = load_yaml(config_path if config_path.exists() else SKILL_ROOT / "config.example.yaml")
    if existing_config and (config.get("setup") or {}).get("initialized") is not True:
        print("[info] local setup is incomplete; completing initialization state")
    selected = choose_external_skills(args)
    install_dir = expand_path(args.install_dir)
    link_targets = choose_link_targets(args, selected)

    if selected:
        ensure_directory(install_dir, dry_run=args.dry_run)
        configure_external_skills(config, selected, install_dir, link_targets, dry_run=args.dry_run)
        update_pipeline(config, selected)
    else:
        external_config = config.setdefault("external_skills", {})
        external_config.setdefault("install_dir", str(install_dir))
        external_config.setdefault("link_targets", [str(path) for path in link_targets])
        print("[ok] no optional external skills selected")

    update_setup_state(config, selected)
    create_runtime_dirs(config, dry_run=args.dry_run)

    if args.dry_run:
        print("[ok] dry run complete; config.yaml was not updated")
        return 0

    write_yaml(config_path, config)
    print("[ok] wrote config.yaml")
    print("[next] Run: python3 scripts/init.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
