#!/usr/bin/env python3
"""
Simple Interactive Telegram Approval Demo.

Clears old updates, sends fresh approval requests, and responds to button clicks.
Run with: uv run python __tests__/integration/run_interactive_demo.py
"""

import asyncio
import logging
import os
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Suppress ALL logging from telegram module completely
logging.disable(logging.CRITICAL)
for logger_name in ['telegram', 'src.integrations.telegram', 'httpx', 'httpcore']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    logging.getLogger(logger_name).disabled = True

from src.integrations.telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    TelegramClient,
    TelegramError,
)


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8566771806:AAG_DzGw5H6cSeK7RsHS2CQAP9qWAb2Iu9o")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "7233821403"))


async def main():
    client = TelegramClient(bot_token=BOT_TOKEN)

    print("=" * 60)
    print("🚀 INTERACTIVE TELEGRAM APPROVAL DEMO")
    print("=" * 60)

    # Step 1: Clear old updates
    print("\n🧹 Clearing old updates...")
    await client.delete_webhook(drop_pending_updates=True)

    # Get and discard any remaining updates
    try:
        updates = await client.get_updates(timeout=1)
        if updates:
            last_id = max(u.update_id for u in updates)
            await client.get_updates(offset=last_id + 1, timeout=1)
        print("   ✅ Old updates cleared")
    except Exception:
        print("   ✅ Ready")

    # Step 2: Send demo approval messages
    print("\n📤 Sending approval requests...")

    demo_messages = {}
    sep = "═" * 32

    # Budget Approval
    msg1 = await client.send_message(
        chat_id=CHAT_ID,
        text=f"""<b>📊 BUDGET APPROVAL REQUEST</b>
{sep}

<b>Title:</b> Q4 Marketing Budget
<b>Amount:</b> $50,000.00
<b>Department:</b> Marketing

<b>Description:</b>
Budget allocation for Q4 marketing campaigns.

<i>👇 Click a button below to respond</i>""",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data="approve_budget"),
                InlineKeyboardButton(text="❌ Reject", callback_data="reject_budget"),
            ],
            [InlineKeyboardButton(text="✏️ Edit", callback_data="edit_budget")],
        ]),
    )
    demo_messages["budget"] = {"id": msg1.message_id, "title": "Q4 Marketing Budget", "status": "pending"}
    print(f"   ✅ Budget approval (msg {msg1.message_id})")

    await asyncio.sleep(0.3)

    # Document Approval
    msg2 = await client.send_message(
        chat_id=CHAT_ID,
        text=f"""<b>📄 DOCUMENT APPROVAL REQUEST</b>
{sep}

<b>Title:</b> Partnership Contract
<b>Type:</b> Legal Agreement
<b>Value:</b> $250,000

<b>Description:</b>
Partnership agreement with TechCorp Inc.

<i>👇 Click a button below to respond</i>""",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data="approve_doc"),
                InlineKeyboardButton(text="❌ Reject", callback_data="reject_doc"),
            ],
            [InlineKeyboardButton(text="✏️ Edit", callback_data="edit_doc")],
        ]),
    )
    demo_messages["doc"] = {"id": msg2.message_id, "title": "Partnership Contract", "status": "pending"}
    print(f"   ✅ Document approval (msg {msg2.message_id})")

    await asyncio.sleep(0.3)

    # Content Approval
    msg3 = await client.send_message(
        chat_id=CHAT_ID,
        text=f"""<b>📝 CONTENT APPROVAL REQUEST</b>
{sep}

<b>Title:</b> Blog Post: AI Trends 2025
<b>Author:</b> Content Team
<b>Tags:</b> #AI #Technology

<b>Preview:</b>
Artificial intelligence continues to transform industries...

<i>👇 Click a button below to respond</i>""",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Publish", callback_data="approve_content"),
                InlineKeyboardButton(text="❌ Reject", callback_data="reject_content"),
            ],
            [InlineKeyboardButton(text="✏️ Edit", callback_data="edit_content")],
        ]),
    )
    demo_messages["content"] = {"id": msg3.message_id, "title": "Blog Post: AI Trends", "status": "pending"}
    print(f"   ✅ Content approval (msg {msg3.message_id})")

    print("\n" + "=" * 60)
    print("📱 CHECK YOUR TELEGRAM NOW!")
    print("   Click the buttons to see them work.")
    print("=" * 60)
    print("\n👂 Listening for button clicks... (Ctrl+C to stop)\n")

    # Track pending rejection reasons
    pending_rejections = {}  # user_id -> key
    last_update_id = 0
    running = True

    while running:
        try:
            updates = await client.get_updates(
                offset=last_update_id + 1 if last_update_id else None,
                timeout=30,
                allowed_updates=["message", "callback_query"],
            )

            for update in updates:
                last_update_id = max(last_update_id, update.update_id)

                # Handle callback (button click)
                if update.callback_query:
                    cb = update.callback_query
                    cb_id = cb.get("id", "")
                    cb_data = cb.get("data", "")
                    user = cb.get("from", {})
                    user_id = user.get("id", 0)
                    username = user.get("username") or user.get("first_name", "User")
                    msg = cb.get("message", {})
                    msg_id = msg.get("message_id")
                    orig_text = msg.get("text", "")

                    # Parse action_key
                    parts = cb_data.split("_", 1)
                    if len(parts) != 2:
                        try:
                            await client.answer_callback_query(cb_id, "Unknown action")
                        except TelegramError:
                            pass
                        continue

                    action, key = parts

                    # Check if this is one of our demos
                    if key not in demo_messages:
                        try:
                            await client.answer_callback_query(cb_id, "Old message - ignored")
                        except TelegramError:
                            pass
                        continue

                    demo = demo_messages[key]

                    print(f"🔔 {username} clicked [{action.upper()}] on {demo['title']}")

                    try:
                        if action == "approve":
                            if demo["status"] != "pending":
                                await client.answer_callback_query(cb_id, f"Already {demo['status']}", show_alert=True)
                                continue

                            demo["status"] = "approved"

                            # Update message
                            await client.edit_message_text(
                                chat_id=CHAT_ID,
                                message_id=msg_id,
                                text=f"""{orig_text}

{sep}

<b>✅ APPROVED</b>
By: @{username}""",
                                parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(text="✅ Status: Approved", callback_data="noop")],
                                ]),
                            )
                            await client.answer_callback_query(cb_id, "✅ Approved!")
                            print(f"   ✅ {demo['title']} APPROVED by @{username}")

                        elif action == "reject":
                            if demo["status"] != "pending":
                                await client.answer_callback_query(cb_id, f"Already {demo['status']}", show_alert=True)
                                continue

                            # Ask for reason
                            pending_rejections[user_id] = key
                            await client.answer_callback_query(cb_id, "Please provide a reason")
                            await client.send_message(
                                chat_id=CHAT_ID,
                                text=f"@{username}, please reply with a reason for rejection\n<i>(or type 'skip' to reject without reason)</i>",
                                parse_mode=ParseMode.HTML,
                                reply_to_message_id=msg_id,
                            )
                            print(f"   ⏳ Waiting for rejection reason from @{username}")

                        elif action == "edit":
                            if demo["status"] != "pending":
                                await client.answer_callback_query(cb_id, f"Already {demo['status']}", show_alert=True)
                                continue

                            demo["status"] = "editing"

                            await client.edit_message_text(
                                chat_id=CHAT_ID,
                                message_id=msg_id,
                                text=f"""{orig_text}

{sep}

<b>✏️ EDITING MODE</b>
Editor: @{username}""",
                                parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(text="✅ Submit Changes", callback_data=f"submit_{key}")],
                                    [InlineKeyboardButton(text="❌ Cancel Edit", callback_data=f"cancel_{key}")],
                                ]),
                            )
                            await client.answer_callback_query(cb_id, "Edit mode - make your changes")
                            print(f"   ✏️ {demo['title']} in EDIT MODE by @{username}")

                        elif action == "submit":
                            demo["status"] = "pending"

                            await client.edit_message_text(
                                chat_id=CHAT_ID,
                                message_id=msg_id,
                                text=f"""<b>📋 {demo['title']} (Edited)</b>
{sep}

<i>Content updated by @{username}</i>

<i>👇 Ready for approval</i>""",
                                parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                    [
                                        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{key}"),
                                        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{key}"),
                                    ],
                                    [InlineKeyboardButton(text="✏️ Edit Again", callback_data=f"edit_{key}")],
                                ]),
                            )
                            await client.answer_callback_query(cb_id, "✅ Changes submitted!")
                            print(f"   📝 {demo['title']} edits SUBMITTED by @{username}")

                        elif action == "cancel":
                            demo["status"] = "pending"

                            await client.edit_message_text(
                                chat_id=CHAT_ID,
                                message_id=msg_id,
                                text=f"""<b>📋 {demo['title']}</b>
{sep}

<i>Edit cancelled</i>

<i>👇 Awaiting approval</i>""",
                                parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                    [
                                        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{key}"),
                                        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{key}"),
                                    ],
                                    [InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit_{key}")],
                                ]),
                            )
                            await client.answer_callback_query(cb_id, "Edit cancelled")
                            print(f"   🚫 Edit CANCELLED for {demo['title']}")

                        elif action == "noop":
                            await client.answer_callback_query(cb_id, "Already processed")

                    except TelegramError as e:
                        if "query is too old" not in str(e).lower():
                            print(f"   ⚠️ Error: {e}")

                # Handle message (rejection reason)
                elif update.message and update.message.text:
                    user = update.message.from_user if hasattr(update.message, 'from_user') else {}
                    if isinstance(user, dict):
                        user_id = user.get("id", 0)
                        username = user.get("username") or user.get("first_name", "User")
                    else:
                        user_id = getattr(user, 'id', 0)
                        username = getattr(user, 'username', None) or getattr(user, 'first_name', 'User')

                    text = update.message.text

                    if user_id in pending_rejections:
                        key = pending_rejections.pop(user_id)
                        demo = demo_messages[key]
                        reason = text.strip() if text.strip().lower() != "skip" else None

                        demo["status"] = "rejected"

                        reason_text = f"\nReason: {reason}" if reason else ""

                        await client.edit_message_text(
                            chat_id=CHAT_ID,
                            message_id=demo["id"],
                            text=f"""<b>❌ REJECTED</b>
{sep}

<b>{demo['title']}</b>
By: @{username}{reason_text}""",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="❌ Status: Rejected", callback_data="noop")],
                            ]),
                        )

                        await client.send_message(
                            chat_id=CHAT_ID,
                            text=f"❌ <b>{demo['title']}</b> has been rejected.",
                            parse_mode=ParseMode.HTML,
                        )

                        print(f"   ❌ {demo['title']} REJECTED by @{username}" + (f" - {reason}" if reason else ""))

        except TelegramError as e:
            if "query is too old" not in str(e).lower():
                print(f"⚠️ Error: {e}")
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            running = False
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            # Handle timeouts and other errors gracefully
            if "timeout" in str(e).lower():
                continue  # Just retry
            print(f"⚠️ Connection error, retrying... ({type(e).__name__})")
            await asyncio.sleep(2)

    await client.close()
    print("\n👋 Demo stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bye!")
