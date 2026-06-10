"""Bot configuration from environment + the allow-list check.

No Telegram or Claude imports here so it stays trivially testable.
"""

import os
from dataclasses import dataclass

DEFAULT_WORKDIR = os.path.expanduser("~/.tokcut/work")
DEFAULT_TARGET = 50.0


@dataclass(frozen=True)
class BotConfig:
    telegram_token: str
    allowed_user_id: int
    workdir: str
    default_target: float


def load_config(env: dict[str, str] | None = None) -> BotConfig:
    """Build a BotConfig from environment variables.

    Raises RuntimeError with an actionable message on missing/invalid vars.
    """
    src = dict(os.environ if env is None else env)

    token = src.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    raw_id = src.get("TOKCUT_ALLOWED_USER_ID", "").strip()
    if not raw_id:
        raise RuntimeError("TOKCUT_ALLOWED_USER_ID is not set")
    try:
        allowed_user_id = int(raw_id)
    except ValueError as exc:
        raise RuntimeError(
            "TOKCUT_ALLOWED_USER_ID must be an integer Telegram user id"
        ) from exc

    workdir = os.path.expanduser(
        src.get("TOKCUT_WORKDIR", "").strip() or DEFAULT_WORKDIR)

    target_raw = src.get("TOKCUT_TARGET", "").strip()
    try:
        default_target = float(target_raw) if target_raw else DEFAULT_TARGET
    except ValueError as exc:
        raise RuntimeError("TOKCUT_TARGET must be a number") from exc

    return BotConfig(token, allowed_user_id, workdir, default_target)


def is_allowed(user_id: int | None, allowed_user_id: int) -> bool:
    """True only for the single allow-listed user. The bot is private."""
    return user_id is not None and user_id == allowed_user_id
