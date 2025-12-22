"""
Interactive Telegram Approval Demo.

This script sends approval requests and LISTENS for button clicks.
When you click Approve/Reject/Edit, it responds in real-time.

Run with: uv run python __tests__/integration/demo_interactive_approval.py

Press Ctrl+C to stop.
"""

import asyncio
import os
import signal
import sys

from src.integrations.telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
    TelegramClient,
    TelegramError,
    Update,
)


class InteractiveApprovalDemo:
    """Interactive demo that responds to button clicks."""

    def __init__(self, bot_token: str, chat_id: int) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = TelegramClient(bot_token=bot_token)
        self.running = False
        self.last_update_id = 0

        # Track our demo messages: {callback_prefix: {message_id, title, type}}
        self.demo_requests: dict[str, dict] = {}
        # Track messages waiting for rejection reason
        self.pending_rejections: dict[int, str] = {}  # user_id -> callback_prefix

    async def send_demo_approval(
        self,
        callback_prefix: str,
        title: str,
        message_text: str,
        approval_type: str,
        include_edit: bool = True,
    ) -> int:
        """Send a demo approval request."""
        buttons = [
            [
                InlineKeyboardButton(
                    text="✅ Approve",
                    callback_data=f"approve_{callback_prefix}"
                ),
                InlineKeyboardButton(
                    text="❌ Reject",
                    callback_data=f"reject_{callback_prefix}"
                ),
            ],
        ]

        if include_edit:
            buttons.append([
                InlineKeyboardButton(
                    text="✏️ Edit",
                    callback_data=f"edit_{callback_prefix}"
                ),
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        message = await self.client.send_message(
            chat_id=self.chat_id,
            text=message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )

        self.demo_requests[callback_prefix] = {
            "message_id": message.message_id,
            "title": title,
            "type": approval_type,
            "status": "pending",
        }

        return message.message_id

    async def handle_callback(self, callback_query: dict) -> None:
        """Handle button click callbacks."""
        callback_id = callback_query.get("id", "")
        callback_data = callback_query.get("data", "")
        user = callback_query.get("from", {})
        user_id = user.get("id", 0)
        username = user.get("username", user.get("first_name", "User"))
        message = callback_query.get("message", {})
        message_id = message.get("message_id")
        original_text = message.get("text", "")

        print(f"🔔 Button clicked: {callback_data} by @{username}")

        # Parse callback data
        parts = callback_data.split("_", 1)
        if len(parts) != 2:
            await self.client.answer_callback_query(callback_id, "Invalid action")
            return

        action, prefix = parts

        # Check if this is one of our demo requests
        if prefix not in self.demo_requests:
            await self.client.answer_callback_query(
                callback_id,
                "Demo request not found",
                show_alert=True
            )
            return

        request = self.demo_requests[prefix]

        if request["status"] != "pending":
            await self.client.answer_callback_query(
                callback_id,
                f"This request was already {request['status']}",
                show_alert=True,
            )
            return

        if action == "approve":
            await self.handle_approve(callback_id, prefix, username, message_id, original_text)
        elif action == "reject":
            await self.handle_reject(callback_id, prefix, user_id, username, message_id)
        elif action == "edit":
            await self.handle_edit(callback_id, prefix, username, message_id, original_text)
        else:
            await self.client.answer_callback_query(callback_id, f"Unknown action: {action}")

    async def handle_approve(
        self,
        callback_id: str,
        prefix: str,
        username: str,
        message_id: int,
        original_text: str,
    ) -> None:
        """Handle approval."""
        request = self.demo_requests[prefix]
        request["status"] = "approved"

        # Update the message
        updated_text = f"""{original_text}

{'═' * 30}

<b>✅ APPROVED</b>
By: @{username}
Status: Complete"""

        # Remove action buttons, show status
        status_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Status: Approved", callback_data="noop")],
            ]
        )

        await self.client.edit_message_text(
            chat_id=self.chat_id,
            message_id=message_id,
            text=updated_text,
            parse_mode=ParseMode.HTML,
            reply_markup=status_keyboard,
        )

        await self.client.answer_callback_query(
            callback_id,
            "✅ Approved successfully!"
        )

        print(f"   ✅ {request['title']} approved by @{username}")

    async def handle_reject(
        self,
        callback_id: str,
        prefix: str,
        user_id: int,
        username: str,
        message_id: int,
    ) -> None:
        """Handle rejection - ask for reason."""
        # Store that we're waiting for a reason
        self.pending_rejections[user_id] = prefix

        await self.client.answer_callback_query(callback_id, "Please provide a reason")

        # Ask for reason
        await self.client.send_message(
            chat_id=self.chat_id,
            text=(
                f"<b>@{username}</b>, please reply with a reason for rejection:\n\n"
                "<i>Type your reason, or send 'skip' to reject without a reason.</i>"
            ),
            parse_mode=ParseMode.HTML,
            reply_to_message_id=message_id,
        )

        print(f"   ⏳ Waiting for rejection reason from @{username}")

    async def complete_rejection(
        self,
        prefix: str,
        username: str,
        reason: str | None,
    ) -> None:
        """Complete the rejection with reason."""
        request = self.demo_requests[prefix]
        request["status"] = "rejected"

        message_id = request["message_id"]

        # Build updated message
        reason_text = f"\nReason: {reason}" if reason else "\nNo reason provided"

        updated_text = f"""<b>❌ REJECTED</b>

<b>Title:</b> {request['title']}
<b>Type:</b> {request['type']}

{'═' * 30}

<b>Status:</b> Rejected
<b>By:</b> @{username}{reason_text}"""

        status_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Status: Rejected", callback_data="noop")],
            ]
        )

        await self.client.edit_message_text(
            chat_id=self.chat_id,
            message_id=message_id,
            text=updated_text,
            parse_mode=ParseMode.HTML,
            reply_markup=status_keyboard,
        )

        # Confirm
        await self.client.send_message(
            chat_id=self.chat_id,
            text=f"❌ <b>{request['title']}</b> has been rejected.",
            parse_mode=ParseMode.HTML,
        )

        print(f"   ❌ {request['title']} rejected by @{username}")

    async def handle_edit(
        self,
        callback_id: str,
        prefix: str,
        username: str,
        message_id: int,
        original_text: str,
    ) -> None:
        """Handle edit request."""
        request = self.demo_requests[prefix]
        request["status"] = "editing"

        # Update message to show editing state
        updated_text = f"""{original_text}

{'═' * 30}

<b>✏️ EDITING</b>
By: @{username}
Status: Awaiting edits..."""

        # Show editing controls
        edit_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Make Changes (Demo)",
                        callback_data=f"changes_{prefix}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="✅ Submit Edits",
                        callback_data=f"submit_{prefix}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Cancel",
                        callback_data=f"cancel_{prefix}"
                    ),
                ],
            ]
        )

        await self.client.edit_message_text(
            chat_id=self.chat_id,
            message_id=message_id,
            text=updated_text,
            parse_mode=ParseMode.HTML,
            reply_markup=edit_keyboard,
        )

        await self.client.answer_callback_query(
            callback_id,
            "Edit mode activated! Make your changes.",
        )

        print(f"   ✏️ {request['title']} being edited by @{username}")

    async def handle_edit_actions(self, callback_query: dict) -> None:
        """Handle edit-related actions (submit, cancel, changes)."""
        callback_id = callback_query.get("id", "")
        callback_data = callback_query.get("data", "")
        user = callback_query.get("from", {})
        username = user.get("username", user.get("first_name", "User"))
        message = callback_query.get("message", {})
        message_id = message.get("message_id")

        parts = callback_data.split("_", 1)
        if len(parts) != 2:
            return

        action, prefix = parts

        if prefix not in self.demo_requests:
            await self.client.answer_callback_query(callback_id, "Request not found")
            return

        request = self.demo_requests[prefix]

        if action == "changes":
            # Demo: show what edits could look like
            await self.client.answer_callback_query(
                callback_id,
                "In production, this opens an edit form. Demo shows changes inline.",
                show_alert=True,
            )

        elif action == "submit":
            # Submit edits - return to pending with updated content
            request["status"] = "pending"

            updated_text = f"""<b>📋 APPROVAL REQUEST (Edited)</b>
{'═' * 30}

<b>Title:</b> {request['title']} <i>(Updated)</i>
<b>Type:</b> {request['type']}

<b>Changes made by:</b> @{username}
<i>Content has been revised.</i>

{'═' * 30}
<i>Awaiting approval...</i>"""

            # Restore approval buttons
            buttons = [
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{prefix}"),
                    InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{prefix}"),
                ],
                [
                    InlineKeyboardButton(text="✏️ Edit Again", callback_data=f"edit_{prefix}"),
                ],
            ]

            await self.client.edit_message_text(
                chat_id=self.chat_id,
                message_id=message_id,
                text=updated_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            )

            await self.client.answer_callback_query(callback_id, "✅ Edits submitted!")
            print(f"   📝 {request['title']} edits submitted by @{username}")

        elif action == "cancel":
            # Cancel edit - return to pending
            request["status"] = "pending"

            updated_text = f"""<b>📋 APPROVAL REQUEST</b>
{'═' * 30}

<b>Title:</b> {request['title']}
<b>Type:</b> {request['type']}

<i>Edit cancelled. Awaiting approval...</i>"""

            buttons = [
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{prefix}"),
                    InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{prefix}"),
                ],
                [
                    InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit_{prefix}"),
                ],
            ]

            await self.client.edit_message_text(
                chat_id=self.chat_id,
                message_id=message_id,
                text=updated_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            )

            await self.client.answer_callback_query(callback_id, "Edit cancelled")
            print(f"   🚫 Edit cancelled for {request['title']}")

    async def handle_message(self, message: dict) -> None:
        """Handle regular messages (for rejection reasons)."""
        user = message.get("from", {})
        user_id = user.get("id", 0)
        username = user.get("username", user.get("first_name", "User"))
        text = message.get("text", "")

        # Check if we're waiting for a rejection reason from this user
        if user_id in self.pending_rejections:
            prefix = self.pending_rejections.pop(user_id)
            reason = text.strip() if text.strip().lower() != "skip" else None
            await self.complete_rejection(prefix, username, reason)

    async def poll_updates(self) -> None:
        """Poll for updates and handle them."""
        print("\n👂 Listening for button clicks... (Press Ctrl+C to stop)\n")

        while self.running:
            try:
                updates = await self.client.get_updates(
                    offset=self.last_update_id + 1 if self.last_update_id else None,
                    timeout=30,
                    allowed_updates=["message", "callback_query"],
                )

                for update in updates:
                    self.last_update_id = max(self.last_update_id, update.update_id)

                    if update.callback_query:
                        callback_data = update.callback_query.get("data", "")
                        callback_id = update.callback_query.get("id", "")

                        try:
                            # Route to appropriate handler
                            if callback_data.startswith(("approve_", "reject_", "edit_")):
                                await self.handle_callback(update.callback_query)
                            elif callback_data.startswith(("submit_", "cancel_", "changes_")):
                                await self.handle_edit_actions(update.callback_query)
                            elif callback_data == "noop":
                                await self.client.answer_callback_query(
                                    callback_id,
                                    "This request has been processed."
                                )
                            else:
                                # Unknown callback - just acknowledge it
                                await self.client.answer_callback_query(
                                    callback_id,
                                    "Button from old demo - ignored"
                                )
                        except TelegramError as e:
                            # Ignore "query is too old" errors from old buttons
                            if "query is too old" not in str(e).lower():
                                print(f"   ⚠️ Callback error: {e}")

                    elif update.message:
                        msg_data = update.message.raw if hasattr(update.message, 'raw') else {}
                        if not msg_data and hasattr(update.message, '__dict__'):
                            msg_data = {
                                "from": update.message.from_user,
                                "text": update.message.text,
                            }
                        await self.handle_message(msg_data)

            except TelegramError as e:
                # Ignore old query errors
                if "query is too old" not in str(e).lower():
                    print(f"⚠️ Telegram error: {e}")
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                await asyncio.sleep(2)

    async def run(self) -> None:
        """Run the interactive demo."""
        self.running = True

        # Delete webhook to enable polling
        await self.client.delete_webhook()

        print("🚀 Interactive Telegram Approval Demo")
        print("=" * 50)
        print(f"Chat ID: {self.chat_id}")
        print("=" * 50)

        # Get bot info
        bot = await self.client.get_me()
        print(f"Bot: @{bot.username}")
        print("=" * 50)

        # Send demo approval requests
        print("\n📤 Sending interactive approval requests...\n")

        sep = "═" * 30

        # 1. Budget Approval
        await self.send_demo_approval(
            callback_prefix="budget1",
            title="Q4 Marketing Budget",
            approval_type="Budget",
            message_text=f"""<b>📊 BUDGET APPROVAL REQUEST</b>
{sep}

<b>Title:</b> Q4 Marketing Budget
<b>Amount:</b> $50,000.00
<b>Department:</b> Marketing

<b>Description:</b>
Budget allocation for Q4 marketing campaigns including digital ads, content, and events.

<i>🕐 Click a button to respond...</i>""",
        )
        print("   ✅ Budget approval sent")

        await asyncio.sleep(0.5)

        # 2. Document Approval
        await self.send_demo_approval(
            callback_prefix="doc1",
            title="Partnership Contract",
            approval_type="Document",
            message_text=f"""<b>📄 DOCUMENT APPROVAL REQUEST</b>
{sep}

<b>Title:</b> Partnership Contract
<b>Type:</b> Legal Agreement
<b>Value:</b> $250,000

<b>Description:</b>
Partnership agreement with TechCorp for joint product development.

<i>🕐 Click a button to respond...</i>""",
        )
        print("   ✅ Document approval sent")

        await asyncio.sleep(0.5)

        # 3. Content Approval
        await self.send_demo_approval(
            callback_prefix="content1",
            title="Blog Post: AI Trends",
            approval_type="Content",
            message_text=f"""<b>📝 CONTENT APPROVAL REQUEST</b>
{sep}

<b>Title:</b> Blog Post: AI Trends 2025
<b>Author:</b> Content Team
<b>Tags:</b> #AI #Technology #Business

<b>Preview:</b>
Artificial intelligence continues to transform industries...

<i>🕐 Click a button to respond...</i>""",
        )
        print("   ✅ Content approval sent")

        print("\n" + "=" * 50)
        print("📱 Check your Telegram! Click the buttons to interact.")
        print("=" * 50)

        # Start polling for updates
        await self.poll_updates()

    async def stop(self) -> None:
        """Stop the demo."""
        self.running = False
        await self.client.close()
        print("\n👋 Demo stopped.")


async def main() -> None:
    """Main entry point."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8566771806:AAG_DzGw5H6cSeK7RsHS2CQAP9qWAb2Iu9o")
    chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "7233821403"))

    demo = InteractiveApprovalDemo(bot_token, chat_id)

    # Handle Ctrl+C gracefully
    loop = asyncio.get_event_loop()

    def signal_handler():
        print("\n\n⏹️ Stopping...")
        asyncio.create_task(demo.stop())

    try:
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    except NotImplementedError:
        # Windows doesn't support add_signal_handler
        pass

    try:
        await demo.run()
    except KeyboardInterrupt:
        await demo.stop()


if __name__ == "__main__":
    asyncio.run(main())
