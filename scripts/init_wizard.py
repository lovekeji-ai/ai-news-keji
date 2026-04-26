"""
ai-news-keji 首次启动 Agent 对话式向导。

用户引导流程集中放在这里，让 scripts/init.py 专注于配置校验、
可选安装命令和 CLI 入口。
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
    "Gmail / Google Workspace：imap.gmail.com，端口 993，开启 SSL；如开启两步验证，请使用 App Password。",
    "iCloud Mail：imap.mail.me.com，端口 993，开启 SSL；请使用 app-specific password。",
    "Outlook / Microsoft 365：outlook.office365.com，端口 993，开启 SSL。",
    "QQ 邮箱：imap.qq.com，端口 993，开启 SSL；请使用授权码。",
    "网易 163 邮箱：imap.163.com，端口 993，开启 SSL；请使用授权码。",
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
    suffix = "默认：是" if default else "默认：否"
    try:
        answer = input(f"{question} [{suffix}] ").strip().lower()
    except EOFError:
        INPUT_EOF_SEEN = True
        print("[warn] 当前环境无法接收交互式输入，使用安全默认值：否")
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
        print("[warn] 当前环境无法接收交互式输入，使用默认值")
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
            print("[warn] 当前环境无法接收交互式输入，使用默认值")
            return default
        if not answer:
            return default
        if answer in choices:
            return answer
        print(f"[warn] 请输入其中一个选项：{choice_text}")


def prompt_multiline(question: str) -> str:
    global INPUT_EOF_SEEN
    print(question)
    print("可以输入一行或多行。输入空行结束；如果直接回车，则使用默认筛选逻辑。")
    lines: list[str] = []
    while True:
        prefix = "> " if not lines else "... "
        try:
            line = input(prefix).rstrip()
        except EOFError:
            INPUT_EOF_SEEN = True
            if not lines:
                print("[warn] 当前环境无法接收交互式输入，使用默认筛选逻辑")
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
        print("[warn] 未在 sources.yaml 或 sources.example.yaml 中找到 Newsletter 来源")
        return

    print("\nNewsletter 来源覆盖：")
    print("请先订阅你希望日报读取的 Newsletter。下方发件人地址会作为邮箱白名单。")
    for item in items:
        name = str(item.get("name") or "未命名")
        category = str(item.get("category") or "未分类")
        frequency = str(item.get("frequency") or "未知频率")
        sender = str(item.get("from") or "未知发件人")
        url = newsletter_subscribe_url(item)
        link = f" | {url}" if url else ""
        print(f"- {name}（{category}，{frequency}）| 发件人：{sender}{link}")


def print_imap_setup_guide() -> None:
    print("\nIMAP 设置：")
    print("1. 先在邮箱设置里开启 IMAP。")
    print("2. 如果邮箱服务商要求，请使用 App Password / 授权码，不要使用明文登录密码。")
    print("3. 邮箱账号和密码只放进环境变量，不写入 config.yaml。")
    for hint in IMAP_HOST_HINTS:
        print(f"- {hint}")


def print_agent_setup_flow(skill_root: Path) -> None:
    print("[info] 进入 ai-news-keji 初始化向导")
    print("[info] 请先在 Agent 对话里确认配置，再由 Agent 写入本地文件。")
    print("\n请按顺序向用户确认：")
    print("1. 外部集成：是否安装 follow-builders、BestBlogs、ak-rss-digest；建议安装全部，用户也可以选择部分或都不安装。")
    print("2. Newsletter：先展示下方订阅源，让用户订阅需要的信息源；再选择 imap、later 或 no。")
    print("3. 如果选择 imap：确认 IMAP host、folder、账号环境变量名、密码/授权码环境变量名。")
    print("4. 输出目录：确认 Markdown 日报默认写入目录。")
    print("5. 个人偏好：建议用户填写关注主题、角色、项目、偏好的内容形式，以及要避开的内容。")
    print_newsletter_subscription_guide(skill_root)
    print_imap_setup_guide()
    print("\nAgent 收集完成后，把答案保存为 JSON，并运行：")
    print("python3 scripts/init.py --answers-file /path/to/ai-news-keji-init-answers.json")
    print("\nJSON 示例：")
    print(
        """{
  "external_skills": ["follow-builders", "bestblogs", "ak-rss-digest"],
  "newsletter": {
    "choice": "later",
    "host": "imap.gmail.com",
    "folder": "INBOX",
    "username_env": "AI_NEWS_IMAP_USERNAME",
    "password_env": "AI_NEWS_IMAP_PASSWORD"
  },
  "output_dir": "~/ai-news-keji/output",
  "preferences": "关注 AI 产品、模型能力、开发者工具和可落地案例；降低融资、招聘和纯营销内容权重。"
}"""
    )


def configure_newsletter(config: dict[str, Any], skill_root: Path) -> None:
    print("\nNewsletter 来源：")
    print_newsletter_subscription_guide(skill_root)
    print_imap_setup_guide()

    choice = prompt_choice("现在接入 Newsletter 来源吗？", ["imap", "later", "no"], default="later")
    email_config = config.setdefault("email", {})
    imap_config = email_config.setdefault("imap", {})

    setup = config.setdefault("setup", {})
    setup["newsletter_choice"] = choice
    mark_setup_step(config, "newsletter_prompted")

    if choice == "imap":
        add_enabled_source(config, "email")
        email_config["mode"] = "imap"
        imap_config["host"] = prompt_text("IMAP 服务器地址", str(imap_config.get("host") or "imap.gmail.com"))
        imap_config["folder"] = prompt_text("IMAP 邮箱文件夹", str(imap_config.get("folder") or "INBOX"))
        imap_config["username_env"] = prompt_text("邮箱账号环境变量名", str(imap_config.get("username_env") or "AI_NEWS_IMAP_USERNAME"))
        imap_config["password_env"] = prompt_text("邮箱密码/授权码环境变量名", str(imap_config.get("password_env") or "AI_NEWS_IMAP_PASSWORD"))
        print(f"[next] 抓取 Newsletter 前，请先设置环境变量 {imap_config['username_env']} 和 {imap_config['password_env']}")
        print("[next] 烟测命令：python3 scripts/fetch-email-imap.py --date YYYY-MM-DD --config config.yaml --sources sources.yaml")
        return

    email_config["mode"] = "none"
    remove_enabled_source(config, "email")
    if choice == "later":
        print("[next] 已暂缓 Newsletter 接入；准备好后可重新运行 python3 scripts/init.py，或手动编辑 config.yaml")
    else:
        print("[ok] 已关闭 Newsletter 来源")


def configure_output_dir(config: dict[str, Any]) -> None:
    print("\n输出目录：")
    paths = config.setdefault("paths", {})
    current = str(paths.get("output_dir") or "~/ai-news-keji/output")
    output_dir = prompt_text("生成 Markdown 日报的默认目录", current)
    paths["output_dir"] = output_dir
    mark_setup_step(config, "output_dir_selected")


def write_preferences_file(
    config: dict[str, Any],
    skill_root: Path,
    preferences: str,
    dry_run: bool = False,
    overwrite: bool = False,
) -> bool:
    paths = config.setdefault("paths", {})
    raw_path = str(paths.get("filter_rules") or "~/ai-news-keji/filter-rules.md")
    paths["filter_rules"] = raw_path
    filter_path = expand_path(raw_path)

    if filter_path.exists() and not overwrite and not prompt_yes_no(f"{filter_path} 已存在。是否用新的偏好覆盖它？", default=False):
        print("[ok] 已保留现有筛选规则文件")
        return False

    example_path = skill_root / "references" / "filter-rules.example.md"
    default_rules = example_path.read_text(encoding="utf-8") if example_path.exists() else ""
    content = "\n".join(
        [
            "# News Filtering Rules",
            "",
            "这些本地筛选规则由 ai-news-keji 初始化向导创建。",
            "",
            "## 个人偏好",
            "",
            preferences,
            "",
            "## 默认基线规则",
            "",
            default_rules,
        ]
    ).rstrip() + "\n"

    print(f"[ok] 写入偏好筛选规则：{filter_path}")
    if dry_run:
        return True
    ensure_parent(filter_path)
    filter_path.write_text(content, encoding="utf-8")
    return True


def configure_preferences(config: dict[str, Any], skill_root: Path, dry_run: bool = False) -> None:
    print("\n个人筛选偏好：")
    print("建议填写：这样日报会按你的兴趣排序，而不是按泛泛的新闻价值排序。")
    preferences = prompt_multiline(
        "你希望这份日报重点关注什么？可以写主题、角色、项目、内容形式，以及要避开的内容。"
    )
    setup = config.setdefault("setup", {})
    mark_setup_step(config, "preferences_prompted")

    if preferences:
        setup["preferences_configured"] = write_preferences_file(config, skill_root, preferences, dry_run=dry_run)
        return

    setup["preferences_configured"] = False
    print("[ok] 暂时使用内置默认筛选逻辑；之后可提供个人 filter_rules 文件")


def run_guided_setup(config: dict[str, Any], skill_root: Path, dry_run: bool = False) -> bool:
    configure_newsletter(config, skill_root)
    configure_output_dir(config)
    configure_preferences(config, skill_root, dry_run=dry_run)
    return not input_was_unavailable()


def apply_newsletter_answer(config: dict[str, Any], answer: Any) -> None:
    if isinstance(answer, str):
        answer = {"choice": answer}
    if not isinstance(answer, dict):
        answer = {}

    choice = str(answer.get("choice") or answer.get("mode") or "later").strip().lower()
    if choice not in {"imap", "later", "no"}:
        raise ValueError("newsletter.choice 必须是 imap、later 或 no")

    email_config = config.setdefault("email", {})
    imap_config = email_config.setdefault("imap", {})
    setup = config.setdefault("setup", {})
    setup["newsletter_choice"] = choice
    mark_setup_step(config, "newsletter_prompted")

    if choice == "imap":
        add_enabled_source(config, "email")
        email_config["mode"] = "imap"
        imap_config["host"] = str(answer.get("host") or imap_config.get("host") or "imap.gmail.com")
        imap_config["folder"] = str(answer.get("folder") or imap_config.get("folder") or "INBOX")
        imap_config["username_env"] = str(
            answer.get("username_env") or imap_config.get("username_env") or "AI_NEWS_IMAP_USERNAME"
        )
        imap_config["password_env"] = str(
            answer.get("password_env") or imap_config.get("password_env") or "AI_NEWS_IMAP_PASSWORD"
        )
        print(f"[next] 抓取 Newsletter 前，请先设置环境变量 {imap_config['username_env']} 和 {imap_config['password_env']}")
        return

    email_config["mode"] = "none"
    remove_enabled_source(config, "email")
    if choice == "later":
        print("[next] Newsletter 接入已标记为稍后配置")
    else:
        print("[ok] 已关闭 Newsletter 来源")


def apply_output_dir_answer(config: dict[str, Any], output_dir: Any) -> None:
    paths = config.setdefault("paths", {})
    paths["output_dir"] = str(output_dir or paths.get("output_dir") or "~/ai-news-keji/output")
    mark_setup_step(config, "output_dir_selected")


def apply_preferences_answer(config: dict[str, Any], skill_root: Path, preferences: Any, dry_run: bool = False) -> None:
    setup = config.setdefault("setup", {})
    mark_setup_step(config, "preferences_prompted")
    text = str(preferences or "").strip()
    if text:
        setup["preferences_configured"] = write_preferences_file(config, skill_root, text, dry_run=dry_run, overwrite=True)
        return
    setup["preferences_configured"] = False
    print("[ok] 未填写个人偏好，将使用内置默认筛选逻辑")


def apply_guided_answers(config: dict[str, Any], skill_root: Path, answers: dict[str, Any], dry_run: bool = False) -> None:
    if not isinstance(answers, dict):
        raise ValueError("answers-file 顶层必须是 JSON object")

    mark_setup_step(config, "external_skills_prompted")
    apply_newsletter_answer(config, answers.get("newsletter", "later"))
    apply_output_dir_answer(config, answers.get("output_dir"))
    apply_preferences_answer(config, skill_root, answers.get("preferences", ""), dry_run=dry_run)
