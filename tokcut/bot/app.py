"""Telegram bot entry point — step 2: full edit round-trip.

Python's job: receive the clip, enforce the allow-list, download it, run
the tokcut edit pipeline in a worker thread (queued — one render at a
time), and send the finished vertical clip back as a *document* so
Telegram doesn't recompress it. Claude Code's job (step 3): caption
wording, output review, and the approve/redo loop.
"""

import asyncio
import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..analysis import probe
from ..caption import check_caption
from ..cli import edit
from ..judge import claude_available, review_output, suggest_caption
from .config import BotConfig, is_allowed, load_config
from .pipeline import derive_caption

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
        "into a vertical TikTok edit and send it back.\n\n"
        "Add a message caption to use it as the on-video caption text.",
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
    file_name = getattr(file_obj, "file_name", "") or ""
    suffix = os.path.splitext(file_name)[1]
    dest = os.path.join(
        cfg.workdir, f"{file_obj.file_unique_id}{suffix or '.mp4'}")
    try:
        tg_file = await context.bot.get_file(file_obj.file_id)
        await tg_file.download_to_drive(dest)
    except Exception as exc:  # noqa: BLE001 — surface any download failure
        log.exception("download failed")
        await msg.reply_text(
            f"⚠️ Couldn't download that file: {exc}\n"
            "Files over 50 MB need a local Bot API server (step 5)."
        )
        return

    caption = (msg.caption or "").strip()
    if not caption and cfg.claude_judge and claude_available():
        await msg.reply_text("🤖 Asking Claude to watch the clip and "
                             "write a caption…")
        try:
            duration = (await asyncio.to_thread(probe, dest))["duration"]
            caption, subject = await asyncio.to_thread(
                suggest_caption, dest, duration)
            await msg.reply_text(
                f"🤖 Claude sees: {subject}\n📝 Caption: “{caption}”")
        except Exception as exc:  # noqa: BLE001 — judgment is best-effort
            log.warning("caption judgment failed: %s", exc)
            await msg.reply_text(
                "🤖 Claude couldn't caption this one — using the filename.")
            caption = ""
    if not caption:
        caption = derive_caption(msg.caption, file_name)
    for warning in check_caption(caption):
        await msg.reply_text(f"⚠️ caption check: {warning}")

    lock: asyncio.Lock = context.application.bot_data["render_lock"]
    if lock.locked():
        await msg.reply_text("⏳ Another render is running — you're queued.")

    async with lock:  # renders are sequential: parallel x265 OOMs the box
        status = await msg.reply_text(f"✂️ Editing with caption: “{caption}”")
        loop = asyncio.get_running_loop()
        progress: list[str] = []

        def notify(line: str) -> None:
            # called from the worker thread — marshal back to the loop
            progress.append(line)
            text = "✂️ " + "\n".join(progress[-6:])
            asyncio.run_coroutine_threadsafe(
                status.edit_text(text[:4000]), loop)

        out = os.path.join(
            cfg.workdir, f"{file_obj.file_unique_id}_tokcut.mp4")
        try:
            await asyncio.to_thread(
                edit, dest, caption,
                output=out, target=cfg.default_target, on_progress=notify)
        except Exception as exc:  # noqa: BLE001 — report, keep bot alive
            log.exception("edit failed")
            await msg.reply_text(f"⚠️ Edit failed: {exc}")
            return

        review_line = ""
        if cfg.claude_judge and claude_available():
            await status.edit_text("🤖 Claude is reviewing the result…")
            try:
                duration = (await asyncio.to_thread(probe, out))["duration"]
                review = await asyncio.to_thread(
                    review_output, out, duration, caption)
                if review["verdict"] == "approve":
                    review_line = f"🤖 review: ✅ {review['notes']}"
                else:
                    issues = "\n".join(f"• {i}" for i in review["issues"])
                    review_line = (f"🤖 review: 🔁 would redo:\n{issues}\n"
                                   f"({review['notes']})")
            except Exception as exc:  # noqa: BLE001 — review is best-effort
                log.warning("output review failed: %s", exc)

        size_mb = os.path.getsize(out) / 1048576
        await msg.reply_text(f"⬆️ Uploading ({size_mb:.1f} MB)…")
        doc_caption = (f"✅ “{caption}”\n"
                       "Muted — add a trending TikTok sound in-app.")
        if review_line:
            doc_caption += f"\n\n{review_line}"
        with open(out, "rb") as fh:
            await msg.reply_document(
                document=fh,
                filename=os.path.basename(out),
                caption=doc_caption[:1024],
            )


def build_application(cfg: BotConfig) -> Application:
    app = Application.builder().token(cfg.telegram_token).build()
    app.bot_data["config"] = cfg
    app.bot_data["render_lock"] = asyncio.Lock()
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
