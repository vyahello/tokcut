"""Telegram bot entry point — step 1 skeleton.

Python's job (here): receive the clip, enforce the allow-list, download it,
run tokcut's deterministic dry-run plan, and reply with it. Claude Code's
job (later, step 3): write the caption, review the rendered output, and
drive the approve/redo loop over subscription OAuth — not wired yet.
"""

import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import BotConfig, is_allowed, load_config
from .pipeline import dry_run_plan, format_plan

log = logging.getLogger("tokcut.bot")


def _user_id(update) -> int | None:
    user = update.effective_user
    return user.id if user else None


async def start(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: BotConfig = context.application.bot_data["config"]
    if not is_allowed(_user_id(update), cfg.allowed_user_id):
        return
    await update.message.reply_text(
        "👋 Send me a clip — as a *file* for best quality — and I'll cut it "
        "into a vertical TikTok edit.",
        parse_mode="Markdown",
    )


async def on_clip(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: BotConfig = context.application.bot_data["config"]
    uid = _user_id(update)
    if not is_allowed(uid, cfg.allowed_user_id):
        log.warning("ignoring clip from unauthorized user %s", uid)
        return

    msg = update.message
    file_obj = msg.video or msg.document
    if file_obj is None:
        return

    await msg.reply_text("⬇️ Downloading…")
    os.makedirs(cfg.workdir, exist_ok=True)
    suffix = os.path.splitext(getattr(file_obj, "file_name", "") or "")[1]
    dest = os.path.join(
        cfg.workdir, f"{file_obj.file_unique_id}{suffix or '.mp4'}")
    try:
        tg_file = await context.bot.get_file(file_obj.file_id)
        await tg_file.download_to_drive(dest)
    except Exception as exc:  # noqa: BLE001 — surface any download failure
        log.exception("download failed")
        await msg.reply_text(
            f"⚠️ Couldn't download that file: {exc}\n"
            "Files over 50 MB need a local Bot API server (coming in step 5)."
        )
        return

    await msg.reply_text("🔍 Analyzing motion…")
    try:
        src, segs, est = dry_run_plan(dest, cfg.default_target)
    except Exception as exc:  # noqa: BLE001 — report, don't crash the bot
        log.exception("analysis failed")
        await msg.reply_text(f"⚠️ Couldn't analyze that file: {exc}")
        return

    await msg.reply_text(format_plan(src, segs, est), parse_mode="Markdown")
    await msg.reply_text(
        "✅ Edit plan ready. Rendering and the Claude-written caption come "
        "in the next steps."
    )


def build_application(cfg: BotConfig) -> Application:
    app = Application.builder().token(cfg.telegram_token).build()
    app.bot_data["config"] = cfg
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.VIDEO | filters.Document.ALL, on_clip))
    return app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    cfg = load_config()
    app = build_application(cfg)
    log.info("tokcut bot starting (allow-listed user=%s, workdir=%s)",
             cfg.allowed_user_id, cfg.workdir)
    app.run_polling()


if __name__ == "__main__":
    main()
