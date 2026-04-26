"""
Interactive first-run wizard for ai-news-keji.

Keep the user-facing onboarding flow here so scripts/init.py can stay focused
on config checks, optional installer commands, and the CLI entrypoint.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


SETUP_STEPS = (
    "external_skills_prompted",
    "newsletter_prompted",
    "output_dir_selected",
    "preferences_prompted",
)

INPUT_EOF_SEEN = False

NEWSLETTER_SUBSCRIBE_URLS = {
    "TLDR AI": "https://tldr.tech/ai",
    "TLDR Dev": "https://tldr.tech/webdev",
    "TLDR Founders": "https://tldr.tech/founders",
    "TLDR": "https://tldr.tech",
    "The Rundown AI": "https://www.rundown.ai",
    "The Neuron": "https://www.theneurondaily.com/subscribe",
    "AI Breakfast": "https://aibreakfast.ai",
    "AI Valley": "https://www.theaivalley.com/subscribe",
    "Ben's Bites": "https://bensbites.co",
    "Latent.Space": "https://www.latent.space",
    "DeepLearning.AI": "https://www.deeplearning.ai/thebatch",
}

IMAP_HOST_HINTS = (
    "Gmail / Google Workspace: imap.gmail.com, port 993, SSL on, use an App Password when required.",
    "iCloud Mail: imap.mail.me.com, port 993, SSL on, use an app-specific password.",
    "Outlook / Microsoft 365: outlook.office365.com, port 993, SSL on.",
    "QQ Mail: imap.qq.com, port 993, SSL on, use an authorization code.",
    "163 Mail: imap.163.com, port 993, SSL on, use an authorization code.",
)


def input_was_unavailable() -> bool:
    return INPUT_EOF_SEEN


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def ensure_parent(path: Path, dry_run: bool = False) -> None:
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def prompt_yes_no(question: str, default: bool = False) -> bool:
    global INPUT_EOF_SEEN
    suffix = "Y/n" if default else "y/N"
    try:
        answer = input(f"{question} [{suffix}] ").strip().lower()
    except EOFError:
        INPUT_EOF_SEEN = True
        print("[warn] no interactive input available; using the safe default: no")
        return False
    if not answer:
        return default
    return answer in {"y", "yes", "是", "好"}


def prompt_text(question: str, default: str = "") -> str:
    global INPUT_EOF_SEEN
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{question}{suffix} ").strip()
    except EOFError:
        INPUT_EOF_SEEN = True
        print("[warn] no interactive input available; using the default value")
        return default
    return answer or default


def prompt_choice(question: str, choices: list[str], default: str) -> str:
    global INPUT_EOF_SEEN
    choice_text = "/".join(choices)
    while True:
        try:
            answer = input(f"{question} ({choice_text}) [{default}] ").strip().lower()
        except EOFError:
            INPUT_EOF_SEEN = True
            print("[warn] no interactive input available; using the default value")
            return default
        if not answer:
            return default
        if answer in choices:
            return answer
        print(f"[warn] choose one of: {choice_text}")


def prompt_multiline(question: str) -> str:
    global INPUT_EOF_SEEN
    print(question)
    print("Enter one or more lines. Press Enter on an empty line to finish, or press Enter immediately to use defaults.")
    lines: list[str] = []
    while True:
        prefix = "> " if not lines else "... "
        try:
            line = input(prefix).rstrip()
        except EOFError:
            INPUT_EOF_SEEN = True
            if not lines:
                print("[warn] no interactive input available; using default filtering rules")
            break
        if not line:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def setup_steps(config: dict[str, Any]) -> dict[str, bool]:
    setup = config.setdefault("setup", {})
    steps = setup.setdefault("steps", {})
    for step in SETUP_STEPS:
        steps.setdefault(step, False)
    return steps


def mark_setup_step(config: dict[str, Any], step: str, value: bool = True) -> None:
    setup_steps(config)[step] = value


def add_enabled_source(config: dict[str, Any], source: str) -> None:
    pipeline = config.setdefault("pipeline", {})
    enabled_sources = pipeline.setdefault("enabled_sources", ["rss", "websites"])
    if source not in enabled_sources:
        enabled_sources.append(source)


def remove_enabled_source(config: dict[str, Any], source: str) -> None:
    pipeline = config.setdefault("pipeline", {})
    enabled_sources = pipeline.setdefault("enabled_sources", [])
    pipeline["enabled_sources"] = [item for item in enabled_sources if item != source]


def load_newsletter_sources(skill_root: Path) -> list[dict[str, Any]]:
    local_sources = skill_root / "sources.yaml"
    example_sources = skill_root / "sources.example.yaml"
    source_path = local_sources if local_sources.exists() else example_sources
    if not source_path.exists():
        return []
    data = load_yaml(source_path)
    return [item for item in data.get("email", []) if isinstance(item, dict)]


def newsletter_subscribe_url(item: dict[str, Any]) -> str:
    if item.get("subscribe_url"):
        return str(item["subscribe_url"])
    return NEWSLETTER_SUBSCRIBE_URLS.get(str(item.get("name") or ""), "")


def print_newsletter_subscription_guide(skill_root: Path) -> None:
    items = load_newsletter_sources(skill_root)
    if not items:
        print("[warn] no newsletter sources found in sources.yaml or sources.example.yaml")
        return

    print("\nNewsletter source coverage:")
    print("Subscribe to the newsletters you want this digest to read. The sender address is used as the mailbox allowlist.")
    for item in items:
        name = str(item.get("name") or "Unnamed")
        category = str(item.get("category") or "uncategorized")
        frequency = str(item.get("frequency") or "unknown")
        sender = str(item.get("from") or "unknown sender")
        url = newsletter_subscribe_url(item)
        link = f" | {url}" if url else ""
        print(f"- {name} ({category}, {frequency}) | from: {sender}{link}")


def print_imap_setup_guide() -> None:
    print("\nIMAP setup:")
    print("1. Enable IMAP in your mailbox settings.")
    print("2. Use an app password or authorization code when your provider requires it.")
    print("3. Store credentials in environment variables, not in config.yaml.")
    for hint in IMAP_HOST_HINTS:
        print(f"- {hint}")


def configure_newsletter(config: dict[str, Any], skill_root: Path) -> None:
    print("\nNewsletter sources:")
    print_newsletter_subscription_guide(skill_root)
    print_imap_setup_guide()

    choice = prompt_choice("Connect newsletter sources now?", ["imap", "later", "no"], default="later")
    email_config = config.setdefault("email", {})
    imap_config = email_config.setdefault("imap", {})

    setup = config.setdefault("setup", {})
    setup["newsletter_choice"] = choice
    mark_setup_step(config, "newsletter_prompted")

    if choice == "imap":
        add_enabled_source(config, "email")
        email_config["mode"] = "imap"
        imap_config["host"] = prompt_text("IMAP host", str(imap_config.get("host") or "imap.gmail.com"))
        imap_config["folder"] = prompt_text("IMAP folder", str(imap_config.get("folder") or "INBOX"))
        imap_config["username_env"] = prompt_text("Username environment variable", str(imap_config.get("username_env") or "AI_NEWS_IMAP_USERNAME"))
        imap_config["password_env"] = prompt_text("Password environment variable", str(imap_config.get("password_env") or "AI_NEWS_IMAP_PASSWORD"))
        print(f"[next] Set {imap_config['username_env']} and {imap_config['password_env']} before fetching newsletters")
        print("[next] Smoke test: python3 scripts/fetch-email-imap.py --date YYYY-MM-DD --config config.yaml --sources sources.yaml")
        return

    email_config["mode"] = "none"
    remove_enabled_source(config, "email")
    if choice == "later":
        print("[next] Newsletter setup deferred; rerun python3 scripts/init.py or edit config.yaml when ready")
    else:
        print("[ok] newsletter sources disabled")


def configure_output_dir(config: dict[str, Any]) -> None:
    print("\nOutput directory:")
    paths = config.setdefault("paths", {})
    current = str(paths.get("output_dir") or "~/ai-news-keji/output")
    output_dir = prompt_text("Default directory for generated Markdown notes", current)
    paths["output_dir"] = output_dir
    mark_setup_step(config, "output_dir_selected")


def write_preferences_file(config: dict[str, Any], skill_root: Path, preferences: str, dry_run: bool = False) -> bool:
    paths = config.setdefault("paths", {})
    raw_path = str(paths.get("filter_rules") or "~/ai-news-keji/filter-rules.md")
    paths["filter_rules"] = raw_path
    filter_path = expand_path(raw_path)

    if filter_path.exists() and not prompt_yes_no(f"{filter_path} already exists. Overwrite it with the new preferences?", default=False):
        print("[ok] existing filter rules left unchanged")
        return False

    example_path = skill_root / "references" / "filter-rules.example.md"
    default_rules = example_path.read_text(encoding="utf-8") if example_path.exists() else ""
    content = "\n".join(
        [
            "# News Filtering Rules",
            "",
            "These local filtering rules were created by ai-news-keji init.",
            "",
            "## Personal Preference",
            "",
            preferences,
            "",
            "## Default Baseline Rules",
            "",
            default_rules,
        ]
    ).rstrip() + "\n"

    print(f"[ok] write preference rules: {filter_path}")
    if dry_run:
        return True
    ensure_parent(filter_path)
    filter_path.write_text(content, encoding="utf-8")
    return True


def configure_preferences(config: dict[str, Any], skill_root: Path, dry_run: bool = False) -> None:
    print("\nPersonal filtering preferences:")
    print("Recommended: add your interests so the daily summary can rank news for you, not for a generic reader.")
    preferences = prompt_multiline(
        "What should this digest care about? Include topics, roles, projects, formats, and things to avoid."
    )
    setup = config.setdefault("setup", {})
    mark_setup_step(config, "preferences_prompted")

    if preferences:
        setup["preferences_configured"] = write_preferences_file(config, skill_root, preferences, dry_run=dry_run)
        return

    setup["preferences_configured"] = False
    print("[ok] using bundled default filtering rules until a personal filter_rules file is provided")


def run_guided_setup(config: dict[str, Any], skill_root: Path, dry_run: bool = False) -> bool:
    configure_newsletter(config, skill_root)
    configure_output_dir(config)
    configure_preferences(config, skill_root, dry_run=dry_run)
    return not input_was_unavailable()
